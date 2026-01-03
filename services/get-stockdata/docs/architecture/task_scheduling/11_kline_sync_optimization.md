# K线同步任务：自适应调度详细设计

## 1. 背景与目标
由于云端数据采集（Baostock）的完成时间不固定（通常在 18:30 - 19:30 之间波动），本地同步任务需要一种“科学”的触发机制，既能尽早开始，又能确保不会同步到未完成的脏数据。

## 2. 核心逻辑：经验预测 + 信号量轮询

整个同步任务分为三个阶段：**经验预测阶段**、**智能等待阶段**、**执行搬运阶段**。

### 2.1 经验预测阶段 (Predictor)
当 `task-orchestrator` 在 18:30 启动任务后，`gsd-worker` 执行以下查询：

**对象**: 腾讯云 MySQL (`alwaysup`)
**SQL**:
```sql
SELECT updated_at 
FROM sync_progress 
WHERE task_name = 'full_market_sync' 
  AND status = 'completed' 
ORDER BY updated_at DESC 
LIMIT 1;
```

**逻辑**:
- 获取前一交易日的实际完成时间（如：`18:55:00`）。
- 计算**目标观察窗口** = `历史完成时间 - 5分钟`（如：`18:50:00`）。

### 2.2 智能等待阶段 (Adaptive Wait)
- 如果当前时间早于“目标观察窗口”：系统进入长休眠（`sleep`），直到进入窗口期。
- 在休眠期间，每 15 分钟“抬头”检查一次云端是否有提早完成的信号。

### 2.3 信号量轮询阶段 (Polling)
进入窗口期后，系统转为高频轮询（每 2 分钟检查一次）：
- **检测目标**: 今日日期且状态为 `completed` 的 `full_market_sync` 记录。
- **阈值校验**: 验证 `total_records` 是否在正常范围（如 > 4800）。

## 3. 异常处理与保障

| 异常场景 | 处理机制 | 动作 |
|:---------|:---------|:----|
| **云端采集失败** | 发现最新日志状态为 `FAILED` | 立即停止本地任务，推送紧急告警 |
| **云端采集超时** | 超过 21:00 仍未出现 SUCCESS 信号 | 停止等待，推送超时告警，记录为 FAILED |
| **数据量异常** | SUCCESS 记录存在但条数过少 | 触发告警，等待人工确认或强制同步 |

## 4. 数据流向定义

- **数据源层 (Source)**:
    - 数据库: 腾讯云 MySQL (`sh-cdb-h7flpxu4...`)
    - 库名: `alwaysup`
    - 核心表: `stock_kline_daily`
- **中转加工层 (Processor)**:
    - 服务: `gsd-worker`
    - 运行环境: 本地 Docker
- **存储目标层 (Target)**:
    - 数据库: 本地 ClickHouse
    - 库名: `stock_data`
    - 核心表: `stock_kline_daily`

## 5. 完整时序示例

### 场景：正常流程（云端 18:55 完成）

```
时间轴          云端 (Baostock → MySQL)              本地 (task-orchestrator → gsd-worker)
─────────────────────────────────────────────────────────────────────────────────
18:30                                                ⏰ task-orchestrator 触发任务
                                                     🚀 gsd-worker 容器启动
                                                     📊 查询历史: 昨日完成于 18:55
                                                     💤 计算等待: sleep 至 18:50

18:50                                                ⏰ 唤醒，进入轮询模式
18:52                                                🔍 检查信号: 未发现今日记录
18:54                                                🔍 检查信号: 未发现今日记录

18:55           ✅ 采集完成
                📝 写入日志:
                   task_name = 'full_market_sync'
                   status = 'completed'
                   total_records = 5000

18:56                                                🔍 检查信号: ✅ 发现 completed
                                                     ✓ 阈值校验: 5000 > 4800 通过
                                                     🚚 开始同步 MySQL → ClickHouse
                                                     
19:08                                                ✅ 同步完成 (耗时 12 分钟)
                                                     📝 写入本地日志:
                                                        sync_execution_logs
                                                        status = 'SUCCESS'
                                                     🎉 容器退出
```

### 场景：异常流程（云端采集失败）

```
时间轴          云端                                 本地
─────────────────────────────────────────────────────────────────────────────────
18:30                                                🚀 启动，查询历史，进入等待
18:50                                                ⏰ 唤醒，开始轮询

19:15           ❌ 采集失败
                📝 写入日志:
                   status = 'failed'
                   error_message = 'Baostock timeout'

19:16                                                🔍 发现 FAILED 记录
                                                     ❌ 停止任务
                                                     🚨 推送告警到企微
                                                     📝 记录本地失败日志
```

## 6. 数据表结构定义

### 6.1 云端采集进度表 (腾讯云 MySQL)

```sql
-- 表名: sync_progress
-- 库名: alwaysup
CREATE TABLE sync_progress (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(50) NOT NULL COMMENT '任务名称',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    status VARCHAR(20) NOT NULL COMMENT '状态: completed, failed, running',
    total_records INT DEFAULT 0 COMMENT '总记录数',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    error_message TEXT COMMENT '错误信息',
    INDEX idx_task_time (task_name, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云端采集任务进度表';
```

**关键字段说明**:
- `task_name`: 云端全市场采集任务固定为 `'full_market_sync'`
- `total_records`: 用于阈值校验（正常应 > 4800）
- `updated_at`: 用于历史预测和今日信号检测
- `status`: completed(完成), failed(失败), running(进行中)

### 6.2 本地同步日志表 (腾讯云 MySQL)

```sql
-- 表名: sync_execution_logs
-- 库名: alwaysup
CREATE TABLE sync_execution_logs (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    status ENUM('RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT') NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INT,
    exit_code INT,
    error_message TEXT,
    metadata JSON,
    INDEX idx_task_time (task_id, start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 7. 复权因子同步策略

K线同步任务**同时处理**复权因子数据：

```
gsd-worker 执行流程:
1. 检测云端信号 (full_market_sync completed)
2. 同步 K线数据 (stock_kline_daily)
3. 同步 复权因子 (stock_adjust_factor)  ← 自动执行
4. 写入本地日志
```

**SQL 示例**:
```sql
-- 云端 MySQL → 本地 ClickHouse
INSERT INTO stock_adjust_factor 
SELECT 
    stock_code,
    ex_date,
    fore_factor,
    back_factor
FROM alwaysup.stock_adjust_factor
WHERE ex_date >= (SELECT MAX(ex_date) FROM stock_adjust_factor);
```

## 8. 本地同步完成后的日志记录

本地同步完成后，`gsd-worker` 必须写入本地日志表：

```python
await task_logger.log_success(
    log_id=log_id,
    duration_seconds=elapsed_time,
    exit_code=0,
    metadata={
        "cloud_completion_time": "18:55:00",
        "local_start_time": "18:56:00",
        "records_synced": 5000,
        "factors_synced": 120
    }
)
```

**用途**:
- 供 `task-orchestrator` 查询任务历史
- 供 API `/api/v1/tasks/{id}/history` 展示
- 用于性能分析和异常排查

## 9. 预期效果
- **及时性**: 平均在云端完成后 2 分钟内开始同步
- **可靠性**: 杜绝了因为采集延迟导致的当日数据缺失
- **资源效率**: 避免容器长时间维持数据库长连接进行无效轮询
- **可追溯性**: 完整的云端→本地日志链路，便于问题定位

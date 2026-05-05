# K线同步任务：自适应调度详细设计 (最终实现版)

## 1. 背景与目标

**核心挑战**: 云端数据采集完成时间不固定,通常在 **18:30 - 19:40** 之间波动。
**目标**: 设计一种"自适应触发机制",在确保数据完整性的前提下,尽早启动本地同步任务,避免同步到未完成的脏数据。

**实际调度时间**: 任务配置为每个交易日 **17:30** 触发（参见 `task-orchestrator/config/tasks.yml`），此时云端数据通常仍在采集中，因此需要自适应调度器在容器内部智能等待。

## 2. 核心逻辑：历史预测 + 自适应轮询

代码实现类: `core.adaptive_scheduler.AdaptiveKLineSyncScheduler`

整个同步任务分为三个阶段：**历史预测阶段**、**智能等待阶段**、**信号量轮询阶段**。

### 2.1 历史预测阶段 (Historical Predictor)
当 `gsd-worker` 启动后 (`jobs.sync_kline`)，首先执行：

**对象**: 腾讯云 MySQL (`alwaysup` 数据库，通过 GOST 隧道 `127.0.0.1:36301` 连接)
**SQL**:
```sql
SELECT updated_at, total_count
FROM sync_progress 
WHERE task_name = 'full_market_sync' 
  AND status = 'completed' 
ORDER BY updated_at DESC 
LIMIT 1;
```

**逻辑**:
- 获取前一交易日的实际完成时间。
- 计算**目标观察窗口** = `历史完成时间 - 缓冲时间(KLINE_SYNC_HISTORY_BUFFER_MIN)`。

### 2.2 智能等待阶段 (Adaptive Wait)
- 如果当前时间早于“目标观察窗口”：系统进入长休眠。
- 在休眠期间，每隔 `KLINE_SYNC_SLEEP_CHECK_INTERVAL_MIN` (默认15分钟) “抬头”检查一次云端是否有提早完成的信号。

### 2.3 信号量轮询阶段 (Polling)
进入窗口期后，系统转为高频轮询（每 `KLINE_SYNC_POLL_INTERVAL_MIN` 分钟检查一次）：
- **检测目标**: 今日日期且状态为 `completed` 的 `full_market_sync` 记录。
- **阈值校验**: 验证 `total_count` 是否大于 `KLINE_SYNC_MIN_RECORDS` (默认4800)。

## 3. 异常处理机制

| 异常场景 | 异常类 | 处理动作 |
|:---------|:-------|:---------|
| **云端采集失败** | `CloudSyncFailedException` | 检测到 `status='failed'`，停止任务，记录FAILED日志 |
| **云端采集超时** | `CloudSyncTimeoutException` | 超过 `KLINE_SYNC_TIMEOUT_TIME` (21:00) 仍未完成，记录FAILED日志 |
| **数据量异常** | `DataVolumeAnomalyException` | `total_count` < 阈值，抛出异常，记录FAILED日志 |
| **数据不一致** | `DataMismatchException` | 同步后 MySQL 与 ClickHouse 行数不匹配，记录FAILED日志 |


## 4. 数据一致性校验 (Consistency Check)

为了防止网络抖动或静默写入失败导致的数据不一致，在完成数据搬运后，必须立即执行**“同步后即时校验” (Verify-After-Write)**。

### 4.1 校验逻辑
- **时机**: `gsd-worker` 完成数据写入 ClickHouse (`insert_dataframe`) 之后，提交 TaskLog 之前。
- **方法**: 对比 Source (MySQL) 和 Target (ClickHouse) 的记录行数。
- **公式**: `MySQL.count(date=today) == ClickHouse.count(date=today)`
- **SQL (ClickHouse)**: `SELECT count() FROM stock_data.stock_kline_daily WHERE trade_date = '{today}'`

### 4.2 处理策略
| 校验结果 | 动作 |
|:---------|:-----|
| **一致** | 校验通过，继续后续步骤（如复权因子同步），最终记录 `SUCCESS` 日志。 |
| **不一致** | 抛出 `DataMismatchException`，记录 `FAILED` 日志。自动重试3次（间隔时间10分钟），失败后退出，依赖告警人工介入或次日自动修复。 |


## 5. 每周深度审计 (Weekly Deep Audit)

为了兜底“静默失败”或上游数据修正，实施每周一次的全量聚合校验。

### 5.1 为什么选择全量？
A股日线数据量级较小（约 2500万行），现代数据库聚合查询耗时在秒级（MySQL < 60s, ClickHouse < 1s）。全量检查能提供 **100% 的数据一致性保证**，且实施成本极低，优于随机抽样。

### 5.2 审计策略：聚合指纹 (Aggregation Fingerprinting)
- **时间**: 每周凌晨 02:00 (避开交易和同步高峰)。
- **维度**: 按 `stock_code` 分组。
- **指纹**: `(Count, Sum(Volume))`。成交量是整数且不仅随价格波动，是最可靠的校验锚点。
- **逻辑**:
    1. MySQL: `SELECT code, count(*), sum(volume) FROM table GROUP BY code`
    2. ClickHouse: `SELECT code, count(), sum(volume) FROM table GROUP BY code`
    3. **Diff**: 对比两边的 Result Map。

### 5.3 自动修复
- **发现不一致**: 标记该股票为 `DIRTY`。
- **动作**: 
    1. 删除本地 ClickHouse 中该股票的全部数据。
    2. 触发 `kline_history_sync` 任务重新全量拉取。
- **报警**: 发送审计报告（包含修复数量）。

## 6. 任务执行日志 (Task Logger)

代码实现类: `core.task_logger.TaskLogger`

本地同步任务的执行结果（无论成功还是失败）都会写入腾讯云 MySQL 的 `sync_execution_logs` 表。

### 6.1 表结构定义
```sql
CREATE TABLE sync_execution_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,    -- 任务名称 (e.g., 'kline_daily_sync')
    status ENUM('RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT') NOT NULL,
    records_processed INT DEFAULT 0,    -- 同步记录数
    details TEXT,                       -- 错误详情或执行摘要
    duration_seconds FLOAT,             -- 耗时(秒)
    execution_time DATETIME NOT NULL,   -- 执行开始时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.2 写入策略
- **成功**: 由 `KLineSyncService` 内部调用 `_log_to_db` 写入 `SUCCESS`。
- **失败**: 由 `jobs.sync_kline` 顶层 `try...except` 捕获异常，调用 `TaskLogger` 写入 `FAILED`，包含完整错误堆栈或消息。

## 7. 复权因子同步策略

代码实现方法: `KLineSyncService.sync_adjust_factors`

采用**智能增量同步**策略，确保高效性。

### 7.1 执行逻辑
1. **查询断点**: 查询本地 ClickHouse `stock_adjust_factor` 表的最大 `ex_date`。
2. **增量获取**: 
   - 如果本地有数据: `SELECT ... FROM stock_adjust_factor WHERE adjust_date > {max_ex_date}`
   - 如果本地无数据: 执行全量查询
3. **写入本地**: 将获取到的新因子批量写入 ClickHouse。

## 8. 配置参数清单

| 环境变量 | 默认值 |说明 |
|:--------|:------|:-----|
| `KLINE_SYNC_HISTORY_BUFFER_MIN` | `5` | 历史预测缓冲时间(分钟) |
| `KLINE_SYNC_SLEEP_CHECK_INTERVAL_MIN` | `15` | 等待期检查间隔(分钟) |
| `KLINE_SYNC_POLL_INTERVAL_MIN` | `2` | 轮询期检查间隔(分钟) |
| `KLINE_SYNC_TIMEOUT_TIME` | `21:00` | 最晚等待时间 |
| `KLINE_SYNC_MIN_RECORDS` | `4800` | 最小合规K线数量 |
| `MYSQL_HOST` | - | 腾讯云MySQL地址 |
| `CLICKHOUSE_HOST` | - | 本地ClickHouse地址 |

## 9. 数据流示意图

```mermaid
graph TD
    Start[启动 sync_kline] --> Mode{模式?}
    Mode -- direct --> Sync[开始同步]
    Mode -- adaptive --> Scheduler[自适应调度器]
    
    Scheduler --> History[历史预测]
    History --> Wait[智能等待]
    Wait --> Poll[信号轮询]
    Poll --> |检测到 completed| Check{数据量校验}
    
    Check -- Pass --> Sync
    Check -- Fail --> Error[记录错误日志]
    
    Sync --> SyncKline[同步K线数据]
    SyncKline --> Verify{一致性校验}
    
    Verify -- Pass --> SyncFactor[同步复权因子]
    Verify -- Fail --> Error
    
    SyncFactor --> Success[记录成功日志]
    
    Error --> End[结束]
    Success --> End
```

## 手动命令

```bash    
 docker run --rm --network host --env-file .env gsd-worker jobs.sync_kline --mode direct
```
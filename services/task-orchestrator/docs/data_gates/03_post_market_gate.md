# 数据门禁 (Gate-3): 盘后深度审计与对账

## 1. 概述

Gate-3 是整个数据采集流程的"终极审计员"，在收盘后执行最严格的数据质量校验。其核心职责是确保当日K线和分笔数据的**完整性**、**连续性**和**一致性**，并在发现异常时自动触发修复流程。

| 属性 | 值 |
| :--- | :--- |
| **执行时间** | 每个交易日 19:18 (CST) |
| **触发方式** | `task-orchestrator` 定时调度 |
| **执行容器** | `gsd-worker` (隔离环境) |
| **结果存储** | 云端 MySQL `alwaysup.data_gate_audits` |

---

## 2. 核心校验项

Gate-3 执行四项独立校验，任何一项不达标都将触发对应的自动修复任务。

### 2.1 K线覆盖率 (云端对齐)

**目标**: 确保本地 ClickHouse 的 K 线数量与云端 MySQL (权威源) 100% 一致。

| 指标 | 来源 | 说明 |
| :--- | :--- | :--- |
| 云端基准 | MySQL `stock_kline_daily` | `SELECT COUNT(*) WHERE trade_date = ?` |
| 本地实测 | ClickHouse `stock_kline_daily` | `SELECT countDistinct(stock_code) WHERE trade_date = ?` |

**公式**: `覆盖率 = ClickHouse 计数 / MySQL 计数 * 100%`

**阈值**: `< 98%` 触发 K 线补采。

> [!TIP]
> 此方法自动忽略停牌股票，无需维护静态名单。

### 2.2 分笔覆盖率

**目标**: 确保当日有分笔数据的股票数量达到预期。

#### 2.2.1 动态基准计算 (Effective A-Stock Count)
审计任务首先从 Redis 中获取当前全量股票名单，并进行动态过滤以确定 A 股基准数量：
1. **数据源**: Redis `metadata:stock_codes` (由 `daily_stock_collection` 维护)。
2. **过滤逻辑**: 仅保留符合 A 股编码规则的股票（沪市 60/68，深市 00/30）。
3. **降级机制**: 若 Redis 不可用，使用常量 `5499` 作为兜底基准。

#### 2.2.2 覆盖率公式
**计算逻辑**:
```sql
SELECT countDistinct(stock_code) 
FROM stock_data.tick_data_intraday 
WHERE trade_date = 'YYYYMMDD'
```
**公式**: `覆盖率 = ClickHouse 记录股票数 / 动态 A 股基准数 * 100%`

**阈值**: `< 95%` 触发补采。

### 2.3 分笔时段完整性 (深度审计)

**目标**: 检查每只股票的分笔数据是否覆盖完整的交易时段 (09:25 - 15:00)。这是通过对每只股票的“分钟轨迹”进行聚合分析实现的。

#### 2.3.1 核心审计 SQL
系统使用双层聚合查询，外层统计异常股票总数，内层计算每只股票的活跃分钟、首笔和末笔时间：
```sql
SELECT 
    stock_code,
    min(tick_time) as first_tick,  -- 首笔时间
    max(tick_time) as last_tick,   -- 末笔时间
    countDistinct(toStartOfMinute(toDateTime(concat('2000-01-01 ', tick_time)))) as active_minutes -- 活跃分钟数
FROM stock_data.tick_data_intraday 
WHERE trade_date = 'YYYYMMDD'
GROUP BY stock_code
```

#### 2.3.2 判定逻辑
| 异常类型 | 判定条件 | 含义 |
| :--- | :--- | :--- |
| **分钟数不足** | `active_minutes < 235` | 理论值为 241 分钟 (09:25 + 240)，允许 6 分钟网络抖动误差 |
| **晚开盘** | `first_tick > '09:25:05'` | 未能抓取到 09:25 的集合竞价首笔数据 |
| **早收盘** | `last_tick < '14:59:55'` | 在 15:00 收盘前数据中断 |

**阈值**: 以上任一条件满足的股票数累计 `> 100` 时，判定为“时段不完整”，触发补采。


> [!NOTE]
> 标准交易日应有 241 个独立分钟 (09:25 + 9:30-11:30 的 120 分钟 + 13:00-15:00 的 120 分钟)。

### 2.4 价格一致性对账

**目标**: 抽样验证分笔数据与 K 线收盘价的一致性。

从核心权重股中抽取 10 只，比对：
- K 线表的 `close_price`
- 分笔表当日最后一笔的 `price`

**阈值**: 差值 `< 0.011` 视为一致。

---

## 3. 自动化修复联动

Gate-3 审计完成后，系统根据结果自动触发对应的修复任务。

| 检测项 | 触发条件 | 修复任务 | 修复策略 |
| :--- | :--- | :--- | :--- |
| K线覆盖率 | `< 98%` | `daily_kline_sync` | 全量重新同步当日 K 线 |
| 分笔覆盖率 | `< 95%` | `repair_tick` | 重新采集配置范围内股票 |
| 时段缺失数 | `> 100` | `repair_tick` | 重新采集配置范围内股票 |

### 3.1 K线自愈同步

当 K 线覆盖率不足时，系统自动触发 `daily_kline_sync` 任务：
1. 对比 ClickHouse 与 MySQL 的当日记录数。
2. 若不一致，物理删除 ClickHouse 中当日数据 (`ALTER TABLE ... DELETE`)。
3. 重新从云端拉取全量当日数据。

### 3.2 分笔补采逻辑 (Repair Logic)

当审计发现覆盖率不足或时段缺失严重时，会由 `PostMarketGateService` 向 `Orchestrator` 发送触发请求。

#### 3.2.1 补采触发流程
1. **决策**: 审计发现异常，记录 `actions_taken` 为 "应当分笔补采"。
2. **驱动**: 调用 `Orchestrator` 的 API 接口：`POST /api/v1/tasks/repair_tick/trigger`。
3. **参数**: 携带当日日期 `{"date": "YYYYMMDD"}`。
4. **调度**: `Orchestrator` 生成一条 `PENDING` 状态的指令。
5. **执行**: `CommandPoller` 轮询到指令，启动 `gsd-worker` 容器运行补采任务。

#### 3.2.2 补采执行细节
补采任务采用 **"定向补采"策略** (Targeted Repair)：
- **执行命令**: `jobs.sync_tick --stock-codes CODE1,CODE2,... --date YYYYMMDD`
- **执行逻辑**:
    - 仅对 Gate-3 标记的**异常股票**进行补采，而非全分片重采。
    - 对每只异常股票重新执行 **"智能搜索矩阵"** (Smart Search Matrix) 采集策略。
    - **数据去重**: ClickHouse 的 `ReplacingMergeTree` 引擎确保补采数据不会产生冲突。

#### 3.2.3 分布式分片补采

分笔数据采用 **3 分片分布式采集** 架构：

| 节点 | IP | Shard ID | 补采触发方式 |
| :--- | :--- | :---: | :--- |
| **Server 41** | 192.168.151.41 | 0 | `CommandPoller` 自动 |
| **Server 58** | 192.168.151.58 | 1 | 手动 SSH |
| **Server 111** | 192.168.151.111 | 2 | 手动 SSH |

> [!WARNING]
> **当前限制**: `repair_tick` 任务仅能在 Server 41 执行 Shard 0 的补采。Shard 1/2 的数据缺失需要**手动 SSH 到对应节点触发**。

**远程节点手动补采命令**：
```bash
# Server 58 (Shard 1)
ssh 192.168.151.58
cd /path/to/microservice-stock
docker compose -f docker-compose.node-58.yml run --rm gsd-worker \
    python -m jobs.sync_tick --scope all --shard-index 1 --shard-total 3 --date YYYYMMDD

# Server 111 (Shard 2)
ssh 192.168.151.111
cd /path/to/microservice-stock
docker compose -f docker-compose.node-111.yml run --rm gsd-worker \
    python -m jobs.sync_tick --scope all --shard-index 2 --shard-total 3 --date YYYYMMDD
```

#### 3.2.4 计划优化：Shard Poller

> [!NOTE]
> **待开发**: 计划在 Server 58/111 部署轻量级 `ShardPoller`，使其可监听云端指令并自动执行分片补采，实现真正的跨节点自动修复。

---

## 4. 手动触发

除自动修复外，可通过向云端 MySQL 插入指令手动触发任务：

### 4.1 重新执行盘后审计
```sql
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES ('post_market_gate', '{"date": "20260115"}', 'PENDING');
```

### 4.2 手动触发 K 线补采
```sql
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES ('repair_kline', '{"date": "20260115"}', 'PENDING');
```

### 4.3 手动触发分笔补采 (全量)
```sql
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES ('repair_tick', '{"date": "20260115"}', 'PENDING');
```

### 4.4 手动触发分笔补采 (指定股票)
> [!NOTE]
> 此功能待 Smart Repair 实现后可用。

```sql
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES ('repair_tick', '{"date": "20260115", "stock_codes": "000001,600519,300750"}', 'PENDING');
```

---

## 5. 技术实现细节

### 5.1 环境隔离
- 审计逻辑运行在独立的 `gsd-worker` 容器中。
- 云端连接通过 SSH 隧道 (端口 36301) 实现。

### 5.2 智能表切换
- **当日审计**: 优先使用 `tick_data_intraday` 表 (实时数据)。
- **历史审计**: 使用 `tick_data` 表 (归档数据)。

### 5.3 审计结果持久化

结果写入云端 `alwaysup.data_gate_audits` 表：

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `trade_date` | DATE | 审计的交易日 |
| `gate_id` | VARCHAR | `GATE_3` |
| `is_complete` | TINYINT | `1`: 全项通过, `0`: 存在异常 |
| `description` | TEXT | 详细结果，如 `K线覆盖率:100% 分笔覆盖率:98% 时段缺失:5` |

### 5.4 企微通知

审计完成后自动发送企业微信通知，报告格式示例：
```
🛡️ 盘后审计报告 (Gate-3) - 2026-01-15
📅 交易日期: 2026-01-15
📈 K线覆盖: 100.0%
📉 分笔覆盖: 98.5%
🕒 连续性审计 (全市场 5423 只):
  - 缺分钟数: 12
  - 晚开盘: 5
  - 早收盘: 3
💰 对账 (样): 10/10
✨ 今日数据质量完美，审计通过。
```

---

## 6. 常见问题 (FAQ)

| 问题 | 原因 | 解决方案 |
| :--- | :--- | :--- |
| K线覆盖率不足 | 云端同步任务失败 | 检查 `daily_kline_sync` 任务状态，或手动触发 |
| 分笔时段大量缺失 | 采集过程中网络波动或 TDX 服务器异常 | 系统会自动触发 `repair_tick` |
| 对账失败 (抽样不一致) | 收盘集合竞价的秒级延迟 | 通常为暂时性问题，系统会自动重试 |
| 审计任务未执行 | `task-orchestrator` 服务异常 | 检查服务状态: `docker logs task-orchestrator` |

---

## 7. 相关文档

- [任务命令格式](file:///home/bxgh/microservice-stock/services/task-orchestrator/docs/development/TASK_COMMAND_FORMAT.md)
- [当前任务调度表](file:///home/bxgh/microservice-stock/services/task-orchestrator/docs/current_task_schedules.md)
- [Gate-2: 盘中数据门禁](file:///home/bxgh/microservice-stock/services/task-orchestrator/docs/data_gates/02_intraday_gate.md)
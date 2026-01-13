# A股全市场分笔盘后全量采集方案 (v3)

## 一、目标
- **范围**: A股全市场 (~5,300 只股票)
- **时机**: 盘后 **15:35** 由各节点 `task-orchestrator` 独立触发
- **策略**: 全量覆盖 (非增量)
- **存储**: 
    - 当日数据 (T日) → `tick_data_intraday`
    - 历史数据 (T-n日) → 直接写入 `tick_data` (映射至 `tick_data_local`)
    - 归档: 次日 09:00 将 `tick_data_intraday` 转移至 `tick_data_local`

---

## 二、表结构说明 (Table Distinctions)

| 表名 (Distributed) | 对应本地表 (Local) | 分区策略 | 角色 |
|--------------------|-------------------|----------|------|
| `tick_data_intraday` | `tick_data_intraday_local` | `PARTITION BY trade_date` | **当日分笔**: 存放 T 日实时及盘后补采数据。分析当日数据时使用。 |
| `tick_data` | `tick_data_local` | `PARTITION BY toYYYYMM(trade_date)` | **历史分笔**: 存档全量历史数据。跨月分表，适合长期存储。 |

---

## 三、设计决策

| 项目 | 决策 |
|------|------|
| 股票列表来源 | Redis → 云端 API → 本地 YAML |
| 数据接口 | **当日**: `transaction(code)` / **历史**: `transactions(code, date=)` |
| 存储目标 | **同步日期=今天**: 写入 `tick_data_intraday` / **否则**: 写入 `tick_data` |
| 调度模式 | 方案 B: 多节点独立 task-orchestrator |
| 数据归档 | 09:00 前置任务 (仅 Server 41 执行) |
| 状态追踪 | Redis Hash (含数据时间范围) |

---

## 四、数据生命周期与迁移

| 时间 | 操作 | 详细逻辑 |
|------|------|----------|
| 15:35 | 采集 T 日补全 | 调用 `transaction()`，数据写入 `tick_data_intraday`。 |
| 09:00 (T+1) | 数据归档 | 1. `INSERT INTO stock_data.tick_data SELECT * FROM stock_data.tick_data_intraday` <br> 2. `TRUNCATE TABLE stock_data.tick_data_intraday` |
| 任意时间 | 补采历史 | 调用 `transactions(date=...)`，数据**直接写入** `tick_data`。 |

---

## 五、采集状态追踪 (Redis)

**Key**: `tick_sync:status:{date}` (Hash)
**Value**: `{status}|{tick_count}|{data_start}|{data_end}|{sync_time}|{error}`

- **data_start/end**: 分笔数据的实际时间范围 (如 `09:25:00` 至 `15:00:00`)，用于验证数据完整性。
- **sync_time**: 本次采集操作的完成时间。

---

## 六、任务配置 (Server 41/58/111)

### 1. 采集任务 (15:35 触发)
各节点根据 `SHARD_INDEX` 采集各自对应的 1,800 只股票。

### 2. 归档任务 (41 独占, 09:00 触发)
负责跨节点数据的最终归档与当日表清理。

---

## 七、验证计划
1. **接口动态切换验证**: 验证同一脚本根据日期参数自动切换接口和目标表。
2. **数据一致性验证**: 验证归档后的数据量与 `tick_data_intraday` 原始量一致。
3. **状态完整性**: 验证 Redis 中 `data_start/end` 字段的提取准确性。

---

## 七、文件变更清单

### task-orchestrator 服务

#### [MODIFY] config/tasks.yml (Server 41)
添加归档任务和 Shard 0 采集任务。

#### [NEW] config/tasks.yml (Server 58)
新建配置文件，仅包含 Shard 1 采集任务。

#### [NEW] config/tasks.yml (Server 111)
新建配置文件，仅包含 Shard 2 采集任务。

---

### docker-compose 配置

#### [MODIFY] docker-compose.node-58.yml
启用 `task-orchestrator` 服务，挂载独立 tasks.yml。

#### [MODIFY] docker-compose.node-111.yml
启用 `task-orchestrator` 服务，挂载独立 tasks.yml。

---

### gsd-worker 服务

#### [MODIFY] src/core/tick_sync_service.py
1. 修改 `sync_stock()` 写入目标表为 `tick_data_intraday`。
2. 添加状态追踪逻辑 (Redis Hash 更新)。
3. 记录数据时间范围 (`min(time)`, `max(time)`)。

#### [MODIFY] src/jobs/sync_tick.py
1. 确保 `--date` 参数为空时使用当日接口 (`transaction()`)。
2. 添加任务开始/结束的状态上报。

---

### ClickHouse DDL

#### [NEW] migrations/add_tick_data_local.sql
创建历史存储表 `tick_data_local` (结构与 `tick_data_intraday` 一致)。

---

## 八、时间估算

| 阶段 | 耗时 |
|------|------|
| Docker Compose 配置 | 0.5h |
| tasks.yml 配置 (3 节点) | 0.5h |
| TickSyncService 修改 | 1h |
| 状态追踪功能 | 1h |
| 集成测试 | 1h |
| **总计** | **4h** |

---

## 九、风险与应对

| 风险 | 应对 |
|------|------|
| 节点时间不同步 | 确保 NTP 服务运行 |
| Redis 不可用 | 本地 YAML 兜底 |
| 某节点采集失败 | 状态追踪 + 次日重试 |
| ClickHouse 写入慢 | 批量写入 + 异步提交 |

---

## 十、验证计划

1. **单元测试**: 状态追踪逻辑、时间范围提取。
2. **集成测试**: 单节点完整采集流程。
3. **分布式测试**: 3 节点同时启动，验证分片不重复。
4. **归档测试**: 验证 09:00 数据迁移逻辑。

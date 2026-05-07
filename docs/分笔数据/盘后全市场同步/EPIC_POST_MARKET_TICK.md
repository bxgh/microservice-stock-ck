# EPIC: 盘后分笔数据全量同步系统

## 1. 项目背景
为了解决盘中实时采集（Intraday Tick）在高频场景下的网络不稳定性及系统负载压力，现将数据采集策略调整为盘后全量同步。本项目旨在建立一套稳定、可审计、高性能的 T+0 盘后分笔数据落地流程。

---

## E1: 物理存储层建设 (Physical Data Layer)
**目标**: 建立符合生产规格的 ClickHouse 存储结构，支持高并发写入与快速指标聚合。

### E1-S1: 存储架构初始化
#### 任务
- [x] **T1**: 执行 DDL 创建 `tick_data_local` (ReplicatedReplacingMergeTree) 与 `tick_data` (Distributed)。 [E1-S1-T1]
- [x] **T2**: 创建 `tick_daily_stats` 物化视图，预聚合主力买卖额。 [E1-S1-T2]
- [x] **T3**: 配置 `tick_data` 表的 TTL 策略（保留 365 天）。 [E1-S1-T3]

#### 验收标准 (AC)
- **AC1**: Given ClickHouse 正常运行, When 执行 DDL 后, Then `stock_data` 库中应能查看到对应的本地表、分布式表及物化视图。
- **AC2**: Given `tick_data` 存在, When 查询 `tick_daily_stats` 结构时, Then 应包含 `buy_volume`、`sell_volume`、`buy_amount` 等关键字段。

---

## E2: 同步引擎优化与适配 (Sync Engine Adaptation)
**目标**: 建立可靠的盘后同步作业，确保全市场 5,000+ 股票的数据在 T+0 日终前完成归档。

### E2-S1: 盘后同步作业编排
#### 任务
- [x] **T1**: 在 `task-orchestrator` 中配置 `daily_tick_sync_standalone` 任务，设定为交易日 18:00 触发。 [E2-S1-T1]
- [x] **T2**: 配置单机高并发参数（`concurrency=60`），利用 Node 41 独占带宽。 [E2-S1-T2]
- [x] **T3**: 集成邮件通知钩子，确保每次同步完成后发送标准报表。 [E2-S1-T3]

#### 验收标准 (AC)
- **AC1**: Given 到达 18:00, When 任务自动触发后, Then 系统应开始抓取全市场分笔数据，且 Node 41 的 CPU 负载处于可控范围。
- **AC2**: Given 任务完成, When 收到邮件时, Then 邮件标题应包含 `Sync Report`, 内容包含 `processed_count` 字段。

---

## E3: 数据校验与审计 (Audit & Self-Healing)
**目标**: 引入 Gate-3 盘后审计逻辑，确保同步结果的准确性。

### E3-S1: 盘后一致性审计 (Gate-3)
#### 任务
- [ ] **T1**: 实现分笔数据总量与 `stock_kline_daily` 成交量的匹配度检查。 [E3-S1-T1]
- [ ] **T2**: 配置自动补采逻辑，当 `daily_volume` 误差 > 1% 时自动触发 `retry_tick`。 [E3-S1-T2]

#### 验收标准 (AC)
- **AC1**: Given 数据同步完成, When 运行 Gate-3 审计脚本后, Then 应产出该日期所有股票的数据完整性评分报告。
- **AC2**: Given 发现单只股票数据缺失, When 触发 `retry_tick` 后, Then 缺失数据应被正确拼缝填补。

---

## E4: 业务派生指标计算 (Derived Metrics Factory)
**目标**: 基于分笔数据产出支持异动评分的核心指标。

### E4-S1: 主力资金流向计算
#### 任务
- [ ] **T1**: 实现基于 `tick_daily_stats` 的主力净流入排名计算逻辑。 [E4-S1-T1]
- [ ] **T2**: 将计算结果写入 `ads_stock_derived_metrics` 派生表。 [E4-S1-T2]

#### 验收标准 (AC)
- **AC1**: Given 分笔统计数据已入库, When 执行计算任务后, Then `ads_stock_derived_metrics` 中应出现当日的 `capital_rank_today` 字段值。

# 分片采集架构审计与故障处理指南 (2026-01-28)

## 1. 任务背景
在分布式 A 股分笔数据（Tick Data）采集系统中，分片采集（Sharding）是平衡负载、规避 IP 封禁和提升吞吐量的核心机制。本文档汇总了分片采集可能出现的异常结果、对应处理策略以及当前系统的实现对齐情况。

---

## 2. 分片采集异常结果矩阵

| 错误类别 | 现象描述 (Symptoms) | 根本原因 (Root Causes) |
| :--- | :--- | :--- |
| **数据空洞 (Gaps)** | 某些股票全天无数据，或特定时间段缺失。 | 分片配置丢失、Worker 启动日期判定错误（6点规则）、名单获取源不一致。 |
| **数据翻倍 (Duplication)** | 同一毫秒出现重复 Tick，ClickHouse 记录数异常。 | 多个分片覆盖重叠、任务配置重复、缺乏写入幂等保护、采集器重启从头开始。 |
| **时间错位 (Sliding)** | 数据日期存储为昨日或明日。 | 节点时区不一致、凌晨时间窗口边界判断模糊、Orchestrator 时间戳传递错误。 |
| **全量静默 (Mute)** | 采集器运行正常但无数据写入。 | API 连接池枯竭（429）、IP 被封锁、Stock Universe 名单过滤逻辑过于严苛。 |
| **热点倾斜 (Skew)** | 部分分片任务耗时极长，部分分片瞬间完成。 | Hash 算法对权重股分配不均、成交活跃股集中在特定分片。 |

---

## 3. 情况处理办法 (Strategies)

### 3.1 预防性策略 (Proactive)
*   **统一 Stock Universe**: 强制通过 Redis 维护标准化的“当日交易股票池”，禁止 Worker 自行推断名单。
*   **断点续传 (Offset Persistence)**: 利用 Redis 记录每个 `(date:code)` 的已采集 offset。
*   **金丝雀校验 (Canary Monitoring)**: 选取 10 只核心权重股（如 600519, 000001），若这些股缺失，直接熔断任务并报警。

### 3.2 治理性策略 (Reactive)
*   **ReplacingMergeTree**: 利用 ClickHouse 引擎特性，通过 `ORDER BY` 键（code, date, time, price, volume）在后台自动合并重复项。
*   **三阶段闭环审计**:
    1.  **Main Sync**: 主动分片采集。
    2.  **Audit**: 扫描 K 线表与 Tick 表的差集。
    3.  **Repair**: 针对性启动 `repair_tick` 任务补全缺失股票。

---

## 4. 现有系统对齐分析 (Code Audit)

### 4.1 已实现项 (Verified)
- [x] **时区锁定**: 全局强制 `Asia/Shanghai`，解决日期漂移。
- [x] **哈希分片互斥**: 使用 `xxhash64` 在 `StockUniverseService` 层面实现物理隔离，确保分片间无数据冲突。
- [x] **双循环采集**: `intraday-tick-collector` 并行执行 Snapshot 和 Tick 增量更新。
- [x] **批量写入缓冲区**: 引入 `ClickHouseWriter` 批量 Flush，缓解 `Too many parts` 压力。

### 4.2 待优化/待处理项 (Optimization Backlog)
- [x] **写入强幂等性**: 已在 `TickWriter` 级别实现 `idempotent` 模式。在执行 `HISTORICAL` 或需要强幂等的目标同步时，会显式调用 `ALTER TABLE ... DELETE` 清理旧数据，彻底解决重复堆积问题。
- [ ] **Worker 权重分配**: 目前分片基于代码 Hash，未来可考虑基于“历史成交活跃度”动态分配分片权重，解决热点倾斜问题。
- [x] **集中式状态机**: 已将 Offset 和同步状态管理重构并入 `gsd_shared.tick.status.SyncStatusTracker`。`TickWorker` 与 `TickSyncService` 现在统一通过该组件进行进度的断点加载与状态报告。

---

## 5. 节点配置建议 (Node 41 实例)
位于 `docker-compose.node-41.yml` 中的 `intraday-tick-collector` 应严格遵循以下参数以保证对齐：
```yaml
environment:
  - SHARD_INDEX=0
  - SHARD_TOTAL=3
  - FLUSH_THRESHOLD=4000
  - POLL_OFFSET=200       # 实时增量深度
  - REDIS_HOST=127.0.0.1  # 状态中心
```

---
**审计人**: Antigravity AI
**日期**: 2026-01-28 20:25

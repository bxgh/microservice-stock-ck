# 盘后分笔数据全市场同步系统 (Post-Market Tick Sync)

## 1. 项目愿景
在每日收盘后（T+0 18:00 后），通过高性能异步抓取技术，将 A 股全市场（5,800+ 只股票）的完整分笔成交数据同步至内网 ClickHouse 存储。该系统取代了原有的盘中实时采集方案，旨在提供更高的数据完整性、更低的系统负载以及更可靠的审计追踪。

## 2. 核心技术承袭
本项目借鉴了“盘中分片采集系统”的成功经验，并针对“盘后批处理”场景进行了以下技术演进：

### 2.1 高并发单机同步 (High-Concurrency Standalone)
*   **技术点**：放弃多节点分片（Sharding），回归单机（Node 41）高并发模式。
*   **优势**：消除分布式节点间的时钟同步和代理透传延迟，利用 41 服务器的高带宽直接写入。
*   **参数**：默认 `concurrency=60`，支持全市场并行抓取。

### 2.2 矩阵拼缝技术 (Matrix-Stitching)
*   **技术点**：沿用盘中采集的序列匹配算法。
*   **用途**：在执行“定向修复（Repair）”模式时，通过前后数据块的特征匹配，确保补采数据与存量数据无缝对接，避免出现重复记录或空洞。

### 2.3 幂等清理与自愈 (Idempotent Purge & Self-Healing)
*   **技术点**：引入“安全阀（Safety Valve）”保护的物理清理逻辑。
*   **用途**：在同步前通过 `ALTER TABLE DELETE` 预清理指定日期的数据。
*   **防御**：严禁无条件的 `TRUNCATE`，清理范围超过全市场 10% 时触发熔断，必须显式 `force_all` 授权。

### 2.4 多级存储架构
*   **本地表 (`tick_data_local`)**：使用 `ReplicatedReplacingMergeTree`，处理由于 API 多次抓取可能产生的极少量重复行。
*   **分布式表 (`tick_data`)**：支持跨节点透明查询。
*   **物化视图 (`tick_daily_stats`)**：采用 `SummingMergeTree` 实时计算每日成交分布，直接支撑上层 `ads_*` 指标计算。

## 3. 任务编排规格
*   **执行时间**：18:00 (T+0 实时数据就绪) / 18:30 (自动补采)。
*   **触发器**：`task-orchestrator` 驱动，采用 `trading_cron` 逻辑。
*   **通知**：遵循 `AGENTS.md` 规范，强制发送包含 `processed_count` 的邮件报告。

## 4. 文档索引
0. [核心需求与任务拆解 (EPIC_POST_MARKET_TICK.md)](EPIC_POST_MARKET_TICK.md)
1. [数据结构与 DDL (01_DATA_SCHEMA.md)](01_DATA_SCHEMA.md)
2. [同步逻辑与作业配置 (02_SYNC_JOBS.md)](02_SYNC_JOBS.md)
3. [审计与校验 (03_AUDIT_LOGIC.md)](03_AUDIT_LOGIC.md)

---
**状态**: 🏗️ 正在从盘中模式迁移至盘后模式  
**负责人**: Antigravity  
**关联章节**: 异动股捕捉 (E2-S1)

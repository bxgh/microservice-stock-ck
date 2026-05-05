# Story Implementation Plan

**Story ID**: 004.01
**Story Name**: 核心策略回测闭环 (Cross-Sectional Backtest Simulator)
**Epic**: 004 (Validation & Intraday Enhancement)
**负责人**: Antigravity
**AI模型**: o1 (架构演进与回测设计)

---

## User Review Required

> [!IMPORTANT]
> 此前我们提到复用 Epic 001 (Story 1.5) 的 `BacktestEngine`，但在梳理架构后发现：
> 1. Epic 001 的引擎是**单标的逐K线 (Single-Stock On-Bar)** 驱动的。
> 2. 我们刚写完的资金团微积分策略是一个**全市场横截面 (Cross-Sectional)** 策略（需要同时拉取数千只股票计算 DTW 距离矩阵并聚类）。
> 
> 若强行嵌套，会导致每测一只股票就把全市场算一遍。因此，本案**提议升维**：基于 Epic-004 的设计文档，为您专门打造一个全新的 **横截面回测仿真器 (`TickClusterSimulator`)**。
> 
> 请您评估并确认：
> 1. **统一门面层 (Strategy Facade)**: 新增一个 `TickClusterStrategy` 外壳类，封装 `SimilarityEngine`, `ClusteringEngine`, `LeadLagAnalyzer` 三大核心件。对外只暴露 `generate_daily_signals(date)`。是否同意？
> 2. **回测仿真器 (Simulator)**: 不同于单股 Loop，我们将以“日期”为轴：每日获取全量 240 维特征矩阵 -> 送入外壳生成集群龙头大名单 -> 执行次日开盘买入 (假设隔日策略) -> 记录盈亏。是否同意此重构逻辑？

---

## 📋 Story概述

### 目标
将前期打造的各个精密齿轮（DTW距离引擎、Leiden社区发现、PageRank龙头挖掘）成功啮合并投入真实战场。通过建立一个按日步进的横截面回测框架，加载历史的分笔特征与收盘价字典，验证该策略能否在历史回放中带来独立且稳定的 Alpha。

### 验收标准
- [ ] 编写 `TickClusterStrategy` 门面类，实现统一的每日特征接收和信号吐出 `[Signal("600000.SH", BUY)]`。
- [ ] 编写 `TickClusterSimulator`，基于时间轴横向扫描全市场。
- [ ] 对模拟信号进行资金簿记 (Portfolio Accounting)，包含最大持仓限制和等权分配买入。
- [ ] 利用现有的 `PerformanceAnalyzer` 算出这段时间的最终无风险收益比（Sharpe Ratio）、最大回撤等并出具 Markdown 报告。

### 依赖关系
- `SimilarityEngine`, `ClusteringEngine`, `LeadLagAnalyzer`
- `epic_part_3_validation_and_enhancement.md`

---

## Proposed Changes

### 架构设计
```mermaid
graph TD
    Data[历史全市场特征矩阵] -->|每日横截面数据| Simulator[TickClusterSimulator]
    Simulator -->|日级别 Matrix| Strategy[TickClusterStrategy 外壳]
    
    subgraph Strategy Core
        Strategy --> Similarity[SimilarityEngine: DTW]
        Similarity --> Clustering[ClusteringEngine: Leiden+Filter]
        Clustering --> LeadLag[LeadLagAnalyzer: PageRank+Trend]
    end
    
    LeadLag -->|EnhancedClusters| Strategy
    Strategy -->|BUY/SELL 信号| Simulator
    Simulator -->|账本清算| Pnl[记录盈亏与每日净值]
    Pnl --> Metrics[PerformanceAnalyzer (复用)]
```

### [Strategic Wrapper]

#### [NEW] src/strategies/tick_cluster_strategy.py
这是一个高度封装的策略实体。
核心方法 `generate_daily_signals(features_matrix: Dict[str, np.ndarray]) -> List[Signal]`
流程：
1. 传入当日特征矩阵；
2. 调度执行 `SimilarityEngine.compute_similarity()`；
3. 将距离矩阵送入 `ClusteringEngine.run_clustering()`，结合换手率、行业、基准等辅助缓存数据清洗出强力资金团；
4. 将残留集群送入 `LeadLagAnalyzer.analyze_clusters()`；
5. 扫描所有的 `EnhancedCluster`，凡是 `trend_phase == FORMATION` 且存在明确 `leader_stock` 的群，对龙头股票生成明天的 `BUY` 信号。

### [Backtest Simulator]

#### [NEW] src/backtest/cross_sectional_simulator.py
解决单标的引擎瓶颈的全市场多空对冲/多头回测器。
核心方法 `run_simulation(start_date, end_date)`
流程：
1. 初始化 `VirtualPortfolio` 模拟账户 (初始 100万元)；
2. 循环交易日列表；
3. 每到一个交易日 `T`，向基础设施调用加载 `T` 日的全量特征矩阵和后复权收盘价；
4. 将数据喂给 `TickClusterStrategy`，拿到该买入的名单列表；
5. 在 `T+1` 日假定以开盘价或收盘价平分买入可用名单（控制单只个股不超过总资金 10%）；同时按规则抛售过期的持仓；
6. 每天记录 `Total Value = Cash + PositionValue`。
7. 返回一条完整的净值曲线（Equity Curve），对接给 `PerformanceAnalyzer`。

---

## Verification Plan

### Automated Tests
1. **策略门面联调断言 (Facade Test)**: 构造 10只假股票组成的假特征矩阵，放入闭环外壳体系。断言能否顺滑地从降维 -> DTW -> 社区发现 -> PageRank 一路走通，并吐出信号。
2. **重度模拟器资金隔离测试 (Simulator Test)**: 不挂载真实策略，而是给模拟器传入固定的 Dummy Signal。断言买入时佣金扣减、金额均分、T+1 平仓金额是否符合完美数学预期的加减乘除。

### Manual Verification
1. 提取一段实际的 A 股 240 维压缩切片给引擎进行回扫，生成 JSON 回测单并人工校验胜率与逻辑一致性。

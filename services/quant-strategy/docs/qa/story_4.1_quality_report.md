# Story 004.01: Quality Assurance Report

**Component**: Cross-Sectional Backtest Simulator & TickClusterStrategy Facade
**Epic**: 004 (Validation & Intraday Enhancement)
**Date**: 2026-02-26

## 1. 结构化设计评测 (Architecture & Design)

- **Facade 模式集成**: 我们引入了 `TickClusterStrategy` 作为统一对外的外壳。这解决了之前各个子模块（Similarity, Clustering, LeadLag）孤立散落、难以一次性调用的问题。该外壳将原先的特征处理矩阵输入，直出标准化的 `Signal` 交易大单，为跨日引擎提供了极大的便利。
- **全市场截面驱动 (Cross-Sectional Simulator)**: 摒弃了第一期针对单股逐 K 线 (On-Bar) 的推演方式，创立了基于日频横切的 `VirtualPortfolio` 和 `CrossSectionalSimulator`。此举一举解决了集群算法如果通过老方案每次单独扫描会导致 $\mathcal{O}(N!)$ 重复调用的世界级难题（N=5000只股票）。

## 2. 代码鲁棒性验证 (Code Robustness)

在 `tests/backtest/test_cross_sectional_simulator.py` 与 `test_tick_cluster_strategy.py` 中的关键断言：
1. **资金限额截断与防爆仓测试 (`test_virtual_portfolio_open_logic`)**: 成功断言资金按照等比例配给给截面上推荐的多只股票。当分配的资金由于触发设置的单只股票最大配比阈值 `max_weight=0.1` 时，引擎进行了正确的砍单约束截断，杜绝“全副身家押注一只游资龙头”的灾难。
2. **模拟 T+1 清算 (`test_virtual_portfolio_close_and_mark_to_market`)**: 成功断言买入后市值（Mark-to-Market）对账簿产生的公允价值波动。当次日执行 `close_all_positions` 时，持仓被顺利转化为现金，并正确扣除了全套的手续费滑点。
3. **Facade 降流测试 (`test_tick_cluster_strategy_facade`)**: 通过喂入三只高度平滑延后的股票 (ABC) 和纯随机噪音股 (XY)。在数学验证上，引擎完美将 XY 筛下，使得只有拥有时差因果关系且由于处于平稳 Formation 阶段的 C (作为领头羊) 输出了 BUY 信号。

## 3. 标准兼容性 (Dependency Compliance)
- 已经将输出重对齐到了老项目 `models.signal` 规定的字段。包括指定 `signal_type=SignalType.LONG`, `priority=Priority.HIGH` 以及要求必需携带 `CST Asia/Shanghai` 属性的 timezone aware DateTimes。

## 4. 遗留缺陷与待办 (Tech Debt)
- 当前 `VirtualPortfolio` 在无法买入时采用了简单跳过处理，未考虑挂单或在盘中由于涨跌停版无法撤盘平仓的逻辑。对于每日强劲选股这种宽泛测试无伤大雅，但在未来引入 T+0 甚至分时拆单时需要改写为严谨的撮合撮合器 (Order Match Engine)。

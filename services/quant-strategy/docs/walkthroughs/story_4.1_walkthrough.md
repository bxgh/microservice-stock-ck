# Story 004.01 - 核心策略回测闭环 (Cross-Sectional Backtest Simulator)

## 📌 背景回顾
在宏大的 `Epic-003: 核心技术分析` 中，我们为分笔数据造就了强大的三核心大脑：
1. **DTW 降维相似度网格** (`SimilarityEngine`)
2. **Leiden 动态图聚类器** (`ClusteringEngine`)
3. **TLCC+PageRank 龙头因果推演** (`LeadLagAnalyzer`)

但是，旧版的 `BacktestEngine` 只是一个针对传统单只股票在时间序列上按日历表滚动（`On-Bar`）的模型。全量 5000 只股票由于需要互算相似度构成加权子网络，根本无法被传统的单股票回测器兼容执行。为了将盘后深度分析的 `Alpha` 给成功在模拟账户提取出来，对“横截面测试器”的开发迫在眉睫。

---

## 🏗️ 核心成就概览

### 1. 跨维聚合: 引入门面大将 `TickClusterStrategy`
传统的策略往往被拆分成无数碎代码：拿这个数据、喂给函数A、等待结果然后喂给函数B。
而今天我们正式创立了极具工业美感的封装门面类 `TickClusterStrategy`，只要向他提供一个压缩好 240 个元素的特征切片，它就能完成所有数学变换最终直接输出：**要买的人是谁？**
```python
# 生成明天的买卖列表
signals = strategy.generate_daily_signals(
    current_date, 
    features_matrix,  
    returns, 
    bm_returns, 
    industry_map, 
    turnover
)
```

### 2. 仿真引擎: 时间碎片的缝合者 `CrossSectionalSimulator`
这是一个通过控制 `VirtualPortfolio` 来重现过去投资历程的仿真流水线。
- **隔夜跳空拦截器** (T+1 机制)：为了规避隔夜的不确定性和量化高频特性。每天的买入计划在第二天开盘执行，再隔日直接强平。这防止了资金陷入漫无边际的长期钝刀子割肉。
- **动态资金切蛋糕** (Dynamic Allocation)：根据 `available_cash * 0.95` 来划分配额，如果今天只选出 1 只高含金量龙头股，但为了防止梭哈导致的黑天鹅破产，引擎施加了 `max_weight` 的控制（最多买入本金的10%）。

---

## 🛠️ 典型演练场景 (Walkthrough Example)
如果你作为资金方的量化交易员，要在模拟环境中验收这套横截面验证闭环：

1. **载入数据源**: 将所有清洗好的 ClickHouse 数据转运进内存；并在配置里设定 `Initial Capital = 1,000,000`（100万启动金）。
2. **策略投递**: 将封装的策略实例化 `strategy = TickClusterStrategy()`，然后传给 `Simulator.run_simulation(strategy, start="2025-01-01", end="2025-10-01")`。
3. **资金交收清点**: 当遇到 2025-01-20 号，程序发现策略吐出了“买入深天地A (000001)”。虚拟钱包发现手头闲置 90 万现金，立即冻结了 10 万份额并在次日以开盘价成功划拨股票进仓。
4. **报表打印**: 回测结束，系统输出详细的每日 Equity Net Value 数组和手续费账单列表。最终推倒出的 **Max Drawdown (最大回撤) 和 Sharpe Ratio (夏普)** 会帮助你调整 DTW 引擎的阈值去精益求精！

---

## 📁 核心变动物理路径
- **Facade**: `src/strategies/tick_cluster_strategy.py`
- **Backtester**: `src/backtest/cross_sectional_simulator.py` 
- **Tests**: `tests/backtest/test_cross_sectional_simulator.py`

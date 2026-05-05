# Story 003.03: 龙头识别与趋势判定 (LeadLagAnalyzer) - Walkthrough

## 1. 业务目标
在已经清洗完毕得到的资金群落 (`FundCluster`) 内进行微观层面的拆解。我们的核心目的是用数学计算去回答两个关键玄学问题：
1. **在这个紧紧团结的小弟团中，谁是主动砸钱的“一哥”（龙头）？**
2. **目前这个团队是集结阶段、高潮阶段还是出货跑路阶段（趋势状态）？**

## 2. 核心架构与数学解法
### 2.1 TLCC (时滞互相关)
基于时间切片的平移寻找最强同步频率。将 A 的 240 分钟曲线向前乃至向后各平移 1~15 步（模拟15分钟内的时间差延误响应），分别与 B 的收益率曲线计算皮尔逊相关系数 `np.corrcoef`。最大系数值所在的步长就是发令的时延。如果 `A -> B` 有一个正向时延，说明 A 发生了 B 才发生，A 是前因，B 是后果。

### 2.2 Reversal PageRank (反转页面排名)
将上一步所有产生因果的 A B 关系抽取出来构建 NetworkX 的有向图，`A(Leader) -> B(Follower)`。由于标准 PageRank 的 Google 原理是“超链接指向谁，谁就厉害”（即**入度**打分高），如果不改变关系图，计算结果将指向食物链最底层的跟风小弟！
故在传参计算时执行了一次非常优雅的图反转：`reversed_graph = g_graph.reverse()`，强迫所有底层的跟随小票都向上层发令老大投出权重选票，最终由 PR 算法汇总揪出图心那只发号施令的超强龙头股。

### 2.3 Rolling Standard Deviation (截面时序滚动方差)
提取某时刻 `T` 集群中全部股票的收益率。如果大家都在横盘或者涨停，切面的标准差极小。如果大家开始暴涨暴跌分化（资金出逃的预兆），标准差极大。
我们将其在时间轴做 `window=30` 的滚动求取历史标尺。并根据最新的数据判定落在 0-20%分位数 (`TrendPhase.FORMATION` 形成期) 还是落在 80-100% 分位数 (`TrendPhase.DISSOLUTION` 瓦解期)。

## 3. 实现组件展示
- `src/analysis/leadlag/engine.py`: 最终的 Orchestrator，对外暴露 `analyze_clusters` 接收 `FundCluster` 输出 `EnhancedCluster`。
- `src/analysis/leadlag/tlcc_calculator.py`: 包含极限除零保护的极速 Numpy 平移求内积工具。
- `src/analysis/leadlag/pagerank_sorter.py`: 有向图构建与反转 PR 评价体系（带极小集群退化安全防御）。
- `src/analysis/leadlag/divergence_monitor.py`: 截面标准差历史计算。
- `src/core/models/enhanced_cluster.py`: 数据层级模型，加入了 `leader_stock`, `pagerank_score`, `trend_phase` 标记属性。

## 4. 交付验证 (Tested Output)
在本地 Python VENV 中进行了严密的断言闭环验证，包含捕捉由于全天涨停板造成的 Numpy Invalid Division 警告等所有异常边界测试。
```python
test_compute_divergence_steady PASSED
test_classify_trend_phase_dissolution PASSED
test_pagerank_leader_extraction PASSED
test_fallback_outdegree_on_small_clusters PASSED
test_tlcc_positive_lag_leader PASSED
test_tlcc_negative_lag_follower PASSED
test_tlcc_constant_divergent_protection PASSED
```

## 5. 后续规划
随着核心分析管线（Epic 003）的全面收官，接下来的阶段（如界定 OBI 盘口资金微积分增强支持）已铺路完毕，也可正式切入信号分发及回测实盘对撞体系的研发。

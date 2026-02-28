# Story 003.02: 社区发现与特征去噪引擎 (ClusteringEngine) - Walkthrough

## 1. 业务目标
基于在 Story 003.01 中吐出的包含千万级关系的 `SimilarityMatrix`，寻找那些由于资金共振导致波动“极为耦合”的资金团伙（Fund Clusters）。在保证不错杀的原则下，极度残酷地滤除“由于随大盘行情上扬”或“身处同一行业板块集体起飞”而导致数据假性共振的“噪音团伙”。

## 2. 核心挑战与架构选择
将纯粹二维浮点距离转换为有效金融洞察面临“分辨率极限”（很容易让全市场的不同行业小票被统摄聚集为一个千股级别的黑洞社区）以及由于全市场流动性枯竭而产生的“平盘假象合并”。
解决方案包括一整套流水线工程（Clustering Pipeline）：
1. **Graph Builder**: 图层构建器。基于 `np.quantile` 对相似度阈值执行动态掐尖（例如取最小的 5% 距离），并使用 `1.0 / (dist + epsilon)` 化为连通边权重。
2. **Leiden Detector**: 使用模块度顶点切分法 (Modularity Vertex Partition) 强制连通度优化。使用从 C++ `igraph` 强力映射的对象避免了 Louvain 算法经常造成的断连小社区合体，聚类质量呈量级提升。
3. **Noise Filters 防火墙**: 定义为 4 大过滤防线，确保入库的是“真独立炒作资金”而不是“机构顺势抱团”：
   - 防线一：小簇抹杀（低于3支标的的联动属于噪音范畴）。
   - 防线二：僵尸停牌抹杀（抹除不具备换手率数据的流动性枯竭簇）。
   - 防线三：大盘中性剥离（与特定指数绝对相关性 `>0.90` 的走势簇将被定义为大盘风口、跟风Beta，直接销毁）。
   - 防线四：行业同质化剔除（簇内单一行业占比高于 `80%` 则判定为单纯行业轮动，只有跨行业的高度联动才是庄主协同）。

## 3. 实现组件展示
- `src/analysis/clustering/engine.py`: 聚落调度入口 `ClusteringEngine#run_clustering()`.
- `src/analysis/clustering/leiden_detector.py`: iGraph 高速 Leiden 实现。
- `src/analysis/clustering/noise_filters.py`: 四大约束防线纯净封装库。
- `src/core/models/cluster.py`: 最终的 `FundCluster` 模型 Schema。

## 4. 交付验证 (Tested Output)
在本地 Python VENV 中进行了全方面的单元与过滤验证：
```python
test_filter_small_clusters PASSED
test_filter_market_beta_clusters PASSED
test_filter_industry_homogeneity PASSED
test_graph_builder_sparsity PASSED
```

## 5. 后续任务衔接
基于生成的具有高信噪比统计特征的数据中心模型 `FundCluster`，后续任务（Story 003.03）将会使用“时滞互相关” (TLCC) 在每个过滤留存的群落里挖掘并标记出“领涨龙头老大”，监控老大异动来发号施令。

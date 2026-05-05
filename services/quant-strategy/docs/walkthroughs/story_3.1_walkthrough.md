# Story 003.01: 两阶段相似度计算引擎 (SimilarityEngine) - Walkthrough

## 1. 业务目标
实现对A股全市场股票（约5000只）的高频 tick 级别、三维特征矩阵（主动买入强度、盘口压力失衡、日内收益率）的相似度精准计算。以作为“主力资金协同性”的核心信号挖掘前置步骤。

## 2. 核心挑战与架构选择
全市场 5000 只股票意味着存在 $C_{5000}^{2} \approx 1250$ 万次组合配对运算，并且每个组合拥有 3 个长度为 240 的分钟级特征向量。若仅使用常规 DTW (O(N²)) 则会耗费数天之久。
为此，我们实现了**两阶段并行算法引擎**：
1. **阶段一（Euclidean Pre-filter）**：利用 `scipy.spatial.distance.pdist` (底层为纯 C) 进行极速的欧氏距离向量粗筛。剔除 95% 差异过大的匹配对。
2. **阶段二（Numba JIT DTW）**：引入 `@njit(fastmath=True)` 将 Python 的嵌套循环 DTW 压制为 C 级别机器码执行，并配合带 `Sakoe-Chiba` 窗口的动态路径剪枝。
3. **并行业务侧（ProcessPoolExecutor）**：运用多进程并发，为了避免 Python 传递大体积 Numpy 数组造成的序列化时间大于计算时间的尴尬，采用了 `global` 热挂载机制预分发特征矩阵。

## 3. 实现组件展示
- `src/analysis/similarity/dtw_core.py`: O(N*W) 的机器码加速版 Sakoe-Chiba 算法。
- `src/analysis/similarity/euclidean_filter.py`: 负责归一化并对齐上三角稀疏索引。
- `src/analysis/similarity/engine.py`: 负责异步切片派发任务，管理 ProcessPool 异常熔断和特征权重汇总。
- `src/core/models/similarity_matrix.py`: 设计为 Pydantic Schema，便于后续图算法节点生成。

## 4. 验证测试 (Tested Output)
在预构的虚拟行情场景下进行了准确度与连通性压测：
```python
test_dtw_exact_match PASSED
test_dtw_shifted_sequence PASSED
test_dtw_large_shift_exceeds_window PASSED
test_engine_end_to_end_flow PASSED
```
时序上的验证证明了 DTW 对于**同一资金操控不同股票造成的时间滞后行为 (Shifted Sequence)** 能完美对齐并给出高相似度评分，打破了欧几里得距离在时序错位上的死角。

## 5. 项目质量数据 (Quality Gate)
- Python类型完全闭环 (Mypy --strict passed)
- 强制格式规范 (Ruff Format & Quality passed)
- 错误降级与保护机制完备：某对计算产生异常 `np.inf` 不会令整个批次（进程）死亡。

## 6. 后续任务衔接
基于生成的 `SimilarityMatrix`，后续的故事线 (Story 003.02) 会将上述数据转化为无向加权图模型，应用 Louvain 或 Leiden 社团聚类算法发现“资金协同团伙”。

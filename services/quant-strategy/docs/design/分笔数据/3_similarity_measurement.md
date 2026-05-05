# 相似度度量与DTW优化

## 1. 问题背景

传统皮尔逊相关系数无法识别**时间错位**的关联：
- 股票A在10:00拉升，股票B在10:05跟随拉升
- 皮尔逊相关系数会判定不相关
- 但实际上它们是强相关的"跟风"关系

**解决方案**：动态时间规整（Dynamic Time Warping, DTW）

---

## 2. DTW算法原理

### 2.1 核心思想

允许序列在时间轴上进行非线性拉伸和压缩，寻找最佳匹配路径。

### 2.2 距离计算

给定两个序列 $X = (x_1, x_2, ..., x_n)$ 和 $Y = (y_1, y_2, ..., y_m)$：

1. **构建距离矩阵**：$d(i,j) = |x_i - y_j|$
2. **累积代价矩阵**：
   $$D(i,j) = d(i,j) + \min\{D(i-1,j), D(i,j-1), D(i-1,j-1)\}$$
3. **DTW距离**：$DTW(X,Y) = D(n,m)$

### 2.3 基础实现

```python
import numpy as np
from numba import jit

@jit(nopython=True)
def dtw_distance(x: np.ndarray, y: np.ndarray) -> float:
    """
    计算两个序列的DTW距离
    
    使用numba加速，约提升100倍性能
    """
    n, m = len(x), len(y)
    
    # 累积代价矩阵
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(x[i-1] - y[j-1])
            D[i, j] = cost + min(D[i-1, j], D[i, j-1], D[i-1, j-1])
    
    return D[n, m]
```

---

## 3. Sakoe-Chiba窗口约束

### 3.1 问题

无约束DTW可能产生不合理匹配：
- 10:00的拉升匹配到14:00的拉升
- 这种"跨半天"的匹配在业务上无意义

### 3.2 解决方案

限制匹配路径只能在对角线附近的"带状区域"内。

```python
@jit(nopython=True)
def dtw_distance_with_window(
    x: np.ndarray, 
    y: np.ndarray, 
    window: int = 15
) -> float:
    """
    带Sakoe-Chiba窗口约束的DTW
    
    Args:
        x, y: 输入序列
        window: 时间窗口约束（分钟），默认15分钟
    
    Returns:
        DTW距禁
    """
    n, m = len(x), len(y)
    
    # 累积代价矩阵，只计算窗口内的区域
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    
    for i in range(1, n + 1):
        # 窗口范围
        j_start = max(1, i - window)
        j_end = min(m, i + window)
        
        for j in range(j_start, j_end + 1):
            cost = abs(x[i-1] - y[j-1])
            D[i, j] = cost + min(D[i-1, j], D[i, j-1], D[i-1, j-1])
    
    return D[n, m]
```

### 3.3 窗口参数选择

| 窗口大小 | 适用场景 | 计算复杂度 |
|----------|----------|------------|
| 5分钟 | 超短线同步 | O(n×5) |
| 15分钟 | 日内跟风（推荐） | O(n×15) |
| 30分钟 | 板块轮动 | O(n×30) |

---

## 4. 计算复杂度优化

### 4.1 问题分析

全市场5000只股票两两计算：
- 股票对数：$C_{5000}^2 = 12,497,500$ 对
- 每对DTW复杂度：$O(240 \times 240) = 57,600$ 次比较
- 总计算量：约 **7200亿次** 基础运算

### 4.2 两阶段筛选策略

```
┌─────────────────────────────────────────────────────────────┐
│            第一阶段：Euclidean距离快速筛选                    │
│                                                             │
│  计算所有股票对的Euclidean距离                               │
│  保留距离最小的5%候选对（约625,000对）                        │
│  复杂度：O(n²×m) ≈ O(5000²×240) ≈ 60亿次                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            第二阶段：DTW精确计算                              │
│                                                             │
│  对625,000个候选对计算DTW距离                                │
│  使用Sakoe-Chiba窗口约束（15分钟）                           │
│  复杂度：O(625,000×240×15) ≈ 22.5亿次                       │
└─────────────────────────────────────────────────────────────┘
```

**总复杂度降低**：从7200亿次降至约80亿次（约90倍加速）

### 4.3 第一阶段实现

```python
from scipy.spatial.distance import cdist
import numpy as np

def euclidean_prefilter(
    vectors: np.ndarray,  # shape: (num_stocks, 240)
    top_percent: float = 0.05
) -> list[tuple[int, int]]:
    """
    Euclidean距离预筛选
    
    Args:
        vectors: 所有股票的特征向量矩阵
        top_percent: 保留的候选对比例
    
    Returns:
        候选股票对索引列表
    """
    num_stocks = vectors.shape[0]
    
    # 计算距离矩阵（上三角）
    distances = cdist(vectors, vectors, metric='euclidean')
    
    # 取上三角索引
    i_indices, j_indices = np.triu_indices(num_stocks, k=1)
    pair_distances = distances[i_indices, j_indices]
    
    # 保留最小的N%
    threshold = np.percentile(pair_distances, top_percent * 100)
    mask = pair_distances <= threshold
    
    candidates = list(zip(
        i_indices[mask].tolist(), 
        j_indices[mask].tolist()
    ))
    
    return candidates
```

### 4.4 第二阶段并行计算

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

async def compute_dtw_batch(
    vectors: np.ndarray,
    candidates: list[tuple[int, int]],
    window: int = 15,
    num_workers: int = 8
) -> dict[tuple[int, int], float]:
    """
    并行计算候选对的DTW距离
    """
    def compute_single(pair):
        i, j = pair
        return (i, j, dtw_distance_with_window(vectors[i], vectors[j], window))
    
    results = {}
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, compute_single, pair)
            for pair in candidates
        ]
        
        for future in asyncio.as_completed(futures):
            i, j, dist = await future
            results[(i, j)] = dist
    
    return results
```

---

## 5. 多特征融合

### 5.1 融合策略

分别计算向量A、B、C的DTW距离，加权求和。

$$D_{total} = \alpha \times DTW(A) + \beta \times DTW(B) + \gamma \times DTW(C)$$

### 5.2 权重推荐

| 特征 | 权重 | 理由 |
|------|------|------|
| 向量A（主动买入） | 0.5 | 最直接反映资金意图 |
| 向量B（盘口失衡） | 0.3 | 反映挂单策略 |
| 向量C（收益率） | 0.2 | 验证作用，避免过度依赖 |

### 5.3 实现

```python
def compute_total_distance(
    stock_i: int,
    stock_j: int,
    vectors_a: np.ndarray,
    vectors_b: np.ndarray,
    vectors_c: np.ndarray,
    window: int = 15,
    weights: tuple = (0.5, 0.3, 0.2)
) -> float:
    """
    计算两只股票的综合DTW距离
    """
    alpha, beta, gamma = weights
    
    dist_a = dtw_distance_with_window(vectors_a[stock_i], vectors_a[stock_j], window)
    dist_b = dtw_distance_with_window(vectors_b[stock_i], vectors_b[stock_j], window)
    dist_c = dtw_distance_with_window(vectors_c[stock_i], vectors_c[stock_j], window)
    
    # 归一化（各特征量纲不同）
    dist_a_norm = dist_a / np.std(vectors_a)
    dist_b_norm = dist_b / np.std(vectors_b)
    dist_c_norm = dist_c / np.std(vectors_c)
    
    return alpha * dist_a_norm + beta * dist_b_norm + gamma * dist_c_norm
```

---

## 6. 输出格式

### 6.1 稀疏距离矩阵

仅存储小于阈值的距离对。

```python
class SparseDistanceMatrix:
    """
    稀疏距离矩阵存储
    
    仅存储距离小于阈值的股票对
    """
    def __init__(self, num_stocks: int):
        self.num_stocks = num_stocks
        self.data = {}  # {(i, j): distance}
    
    def add(self, i: int, j: int, distance: float):
        if i < j:
            self.data[(i, j)] = distance
        else:
            self.data[(j, i)] = distance
    
    def get(self, i: int, j: int) -> float:
        if i == j:
            return 0.0
        key = (min(i, j), max(i, j))
        return self.data.get(key, float('inf'))
    
    def to_adjacency_list(self) -> dict[int, list[tuple[int, float]]]:
        """转换为邻接表格式，用于图构建"""
        adj = {i: [] for i in range(self.num_stocks)}
        for (i, j), dist in self.data.items():
            adj[i].append((j, dist))
            adj[j].append((i, dist))
        return adj
```

### 6.2 Redis存储格式

```python
def save_distance_matrix(
    date: str, 
    matrix: SparseDistanceMatrix,
    redis_client
):
    """
    存储距离矩阵到Redis
    
    Key: dtw_matrix:{date}
    Value: JSON序列化的稀疏矩阵
    """
    key = f"dtw_matrix:{date}"
    value = json.dumps({
        "num_stocks": matrix.num_stocks,
        "pairs": [
            {"i": i, "j": j, "d": d} 
            for (i, j), d in matrix.data.items()
        ]
    })
    redis_client.set(key, value, ex=86400 * 7)  # 7天过期
```

---

## 7. 参数配置

```yaml
similarity_measurement:
  # DTW参数
  dtw:
    window: 15  # Sakoe-Chiba窗口（分钟）
    
  # 预筛选参数
  prefilter:
    method: "euclidean"
    top_percent: 0.05  # 保留前5%候选对
    
  # 多特征融合权重
  weights:
    vector_a: 0.5
    vector_b: 0.3
    vector_c: 0.2
    
  # 并行计算
  parallel:
    num_workers: 8
```

---

## 8. 参数敏感性测试

| 参数 | 测试范围 | 评估指标 |
|------|----------|----------|
| DTW窗口 | [5, 10, 15, 20, 30] | Cluster稳定性 |
| 预筛选比例 | [1%, 3%, 5%, 10%] | 召回率 vs 计算时间 |
| 融合权重 | 不同组合 | 回测收益 |

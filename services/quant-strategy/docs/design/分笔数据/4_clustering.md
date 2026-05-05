# 社群发现与聚类算法

## 1. 概述

基于稀疏距离矩阵，使用图论算法将股票划分为不同的"帮派"（Cluster）。

**为什么不用K-Means**：
- K-Means需要预设聚类数量K，主观性强
- K-Means假设簇是球形的，不适合复杂网络结构
- 图论算法可自动发现社区数量和边界

---

## 2. 图构建

### 2.1 节点与边定义

| 元素 | 定义 |
|------|------|
| **节点 (Node)** | 每只股票 |
| **边 (Edge)** | DTW距离小于阈值的股票对 |
| **边权重** | $w_{ij} = \frac{1}{1 + DTW_{ij}}$（距离越小，权重越大） |

### 2.2 阈值确定

**自适应阈值策略**：取全市场DTW距离分布的某个分位数。

```python
def compute_adaptive_threshold(
    distance_matrix: SparseDistanceMatrix,
    percentile: float = 5.0
) -> float:
    """
    计算自适应连接阈值
    
    Args:
        distance_matrix: 稀疏距离矩阵
        percentile: 分位数（推荐5%）
    
    Returns:
        阈值
    """
    distances = list(distance_matrix.data.values())
    return np.percentile(distances, percentile)
```

### 2.3 图构建实现

```python
import networkx as nx

def build_similarity_graph(
    distance_matrix: SparseDistanceMatrix,
    stock_codes: list[str],
    threshold: float
) -> nx.Graph:
    """
    构建相似度图
    
    Args:
        distance_matrix: 稀疏距离矩阵
        stock_codes: 股票代码列表（索引对应距离矩阵）
        threshold: 连接阈值
    
    Returns:
        NetworkX图对象
    """
    G = nx.Graph()
    
    # 添加所有股票作为节点
    for i, code in enumerate(stock_codes):
        G.add_node(i, stock_code=code)
    
    # 添加边（距离小于阈值）
    for (i, j), dist in distance_matrix.data.items():
        if dist < threshold:
            weight = 1.0 / (1.0 + dist)
            G.add_edge(i, j, weight=weight, distance=dist)
    
    return G
```

---

## 3. Louvain社区发现算法

### 3.1 算法原理

**目标**：最大化图的模块度（Modularity）。

$$Q = \frac{1}{2m} \sum_{ij} \left[ A_{ij} - \frac{k_i k_j}{2m} \right] \delta(c_i, c_j)$$

其中：
- $A_{ij}$：邻接矩阵
- $k_i$：节点i的度
- $m$：总边数
- $c_i$：节点i所属社区
- $\delta$：Kronecker函数

### 3.2 算法步骤

1. **初始化**：每个节点独立成一个社区
2. **局部优化**：遍历每个节点，尝试移动到邻居社区，选择模块度增益最大的移动
3. **聚合**：将同一社区的节点合并为超级节点
4. **迭代**：对新图重复步骤2-3，直到模块度不再增加

### 3.3 实现

```python
import community as community_louvain  # pip install python-louvain

def detect_communities(
    G: nx.Graph,
    resolution: float = 1.0
) -> dict[int, int]:
    """
    Louvain社区发现
    
    Args:
        G: 相似度图
        resolution: 分辨率参数（越大社区越小）
    
    Returns:
        {node_id: community_id}
    """
    partition = community_louvain.best_partition(
        G, 
        weight='weight',
        resolution=resolution
    )
    return partition
```

### 3.4 Leiden算法（可选）

Leiden是Louvain的改进版，解决了社区断裂问题。

```python
import leidenalg
import igraph as ig

def detect_communities_leiden(
    G: nx.Graph,
    resolution: float = 1.0
) -> dict[int, int]:
    """
    Leiden社区发现（更精确）
    """
    # NetworkX转igraph
    edges = list(G.edges())
    weights = [G[u][v]['weight'] for u, v in edges]
    ig_graph = ig.Graph.TupleList(edges, directed=False)
    ig_graph.es['weight'] = weights
    
    # Leiden算法
    partition = leidenalg.find_partition(
        ig_graph,
        leidenalg.RBConfigurationVertexPartition,
        weights='weight',
        resolution_parameter=resolution
    )
    
    # 转换为dict格式
    result = {}
    for comm_id, members in enumerate(partition):
        for node in members:
            result[node] = comm_id
    
    return result
```

---

## 4. 噪音过滤

### 4.1 过滤规则

发现的Cluster中存在噪音，需要过滤：

| 规则 | 阈值 | 理由 |
|------|------|------|
| **大盘相关性** | > 0.8 | 因大盘涨而普涨，无信息量 |
| **成员数量** | < 3 | 样本太少，不可靠 |
| **平均换手率** | < 0.5% | 流动性差，不具操作性 |

### 4.2 实现

```python
def filter_clusters(
    partition: dict[int, int],
    stock_features: pd.DataFrame,  # 包含日收益率、换手率等
    index_return: float,  # 沪深300当日收益率
    min_size: int = 3,
    max_correlation: float = 0.8,
    min_turnover: float = 0.005
) -> dict[int, list[int]]:
    """
    过滤噪音Cluster
    
    Args:
        partition: {node_id: cluster_id}
        stock_features: 股票特征数据
        index_return: 基准指数收益率
        min_size: 最小成员数
        max_correlation: 最大大盘相关性
        min_turnover: 最小平均换手率
    
    Returns:
        {cluster_id: [node_ids]}（过滤后）
    """
    # 按Cluster分组
    clusters = {}
    for node, cluster in partition.items():
        if cluster not in clusters:
            clusters[cluster] = []
        clusters[cluster].append(node)
    
    valid_clusters = {}
    
    for cluster_id, members in clusters.items():
        # 规则1：成员数量
        if len(members) < min_size:
            continue
        
        # 获取成员特征
        member_codes = [stock_features.iloc[m]['stock_code'] for m in members]
        member_returns = stock_features[stock_features['stock_code'].isin(member_codes)]['return']
        member_turnovers = stock_features[stock_features['stock_code'].isin(member_codes)]['turnover']
        
        # 规则2：大盘相关性
        correlation = np.corrcoef(member_returns.values, [index_return] * len(members))[0, 1]
        if abs(correlation) > max_correlation:
            continue
        
        # 规则3：平均换手率
        avg_turnover = member_turnovers.mean()
        if avg_turnover < min_turnover:
            continue
        
        valid_clusters[cluster_id] = members
    
    return valid_clusters
```

---

## 5. 稳定性验证

### 5.1 跨日Jaccard相似度

评估Cluster成员的跨日稳定性。

```python
def compute_cluster_stability(
    cluster_today: set[str],  # 今日成员股票代码
    cluster_yesterday: set[str]  # 昨日成员股票代码
) -> float:
    """
    计算Jaccard相似度
    
    J = |A ∩ B| / |A ∪ B|
    
    返回：0-1，越大越稳定
    """
    intersection = cluster_today & cluster_yesterday
    union = cluster_today | cluster_yesterday
    
    if len(union) == 0:
        return 0.0
    
    return len(intersection) / len(union)
```

### 5.2 稳定性分类

| 稳定度 | 分类 | 操作建议 |
|--------|------|----------|
| ≥ 0.7 | 持续性热点 | 可跟踪 |
| 0.4 - 0.7 | 演化中 | 观察 |
| < 0.4 | 一日游 | 忽略 |

---

## 6. 输出格式

### 6.1 Cluster结构

```python
@dataclass
class Cluster:
    cluster_id: int
    date: str
    members: list[str]  # 股票代码列表
    
    # 聚合特征
    avg_return: float  # 平均收益率
    avg_turnover: float  # 平均换手率
    correlation_with_index: float  # 与沪深300相关性
    
    # 稳定性
    stability_score: float  # 跨日稳定性
    days_existed: int  # 连续存在天数
    
    # 边界
    internal_density: float  # 内部连接密度
    external_density: float  # 外部连接密度
```

### 6.2 持久化

```python
def save_clusters(
    date: str,
    clusters: list[Cluster],
    clickhouse_client
):
    """
    存储Cluster到ClickHouse
    """
    data = [
        {
            "date": cluster.date,
            "cluster_id": cluster.cluster_id,
            "members": ",".join(cluster.members),
            "avg_return": cluster.avg_return,
            "avg_turnover": cluster.avg_turnover,
            "correlation": cluster.correlation_with_index,
            "stability": cluster.stability_score,
            "days_existed": cluster.days_existed,
        }
        for cluster in clusters
    ]
    
    clickhouse_client.insert("tick_clusters", data)
```

---

## 7. 参数配置

```yaml
clustering:
  # 图构建
  graph:
    threshold_percentile: 5  # 距离阈值分位数
    
  # 社区发现
  algorithm: "louvain"  # louvain / leiden
  resolution: 1.0
  
  # 噪音过滤
  filter:
    min_size: 3
    max_correlation: 0.8
    min_turnover: 0.005
    
  # 稳定性
  stability:
    lookback_days: 5  # 回溯天数
    min_stability: 0.4  # 最小稳定性阈值
```

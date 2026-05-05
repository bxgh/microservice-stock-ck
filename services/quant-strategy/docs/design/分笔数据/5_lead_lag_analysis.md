# 龙头识别与趋势推演

## 1. 概述

在识别出Cluster（一伙人）后，需要确定：
1. **谁是龙头（Leader）**：领先启动的股票
2. **趋势阶段**：合力期（买入）还是瓦解期（卖出）

---

## 2. 时滞互相关 (TLCC)

### 2.1 算法原理

计算两只股票在不同时间位移下的相关系数，找到最佳匹配的时滞。

$$TLCC(\tau) = \text{corr}(X_t, Y_{t+\tau})$$

- $\tau > 0$：X领先Y
- $\tau < 0$：Y领先X
- $\tau = 0$：同步

### 2.2 实现

```python
import numpy as np
from scipy.stats import pearsonr

def compute_tlcc(
    x: np.ndarray,  # 股票A的分钟收益率序列
    y: np.ndarray,  # 股票B的分钟收益率序列
    max_lag: int = 30  # 最大时滞（分钟）
) -> tuple[int, float]:
    """
    计算时滞互相关
    
    Args:
        x, y: 分钟收益率序列（240维）
        max_lag: 最大时滞范围
    
    Returns:
        (optimal_lag, max_correlation)
        optimal_lag > 0 表示X领先Y
    """
    n = len(x)
    correlations = []
    
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            x_segment = x[:n-lag]
            y_segment = y[lag:]
        else:
            x_segment = x[-lag:]
            y_segment = y[:n+lag]
        
        if len(x_segment) < 10:
            correlations.append((lag, 0.0))
            continue
        
        corr, _ = pearsonr(x_segment, y_segment)
        correlations.append((lag, corr))
    
    # 找到最大相关系数对应的时滞
    optimal_lag, max_corr = max(correlations, key=lambda x: x[1])
    
    return optimal_lag, max_corr
```

### 2.3 时间窗口设置

| 场景 | max_lag | 说明 |
|------|---------|------|
| 日内分析 | 30分钟 | 捕捉日内跟风 |
| 跨日分析 | 120分钟 | 需拼接多日数据 |

---

## 3. 领先-滞后矩阵

### 3.1 构建

对Cluster内所有股票对计算TLCC，构建有向邻接矩阵。

```python
def build_lead_lag_matrix(
    cluster_members: list[int],  # 成员节点ID
    returns: np.ndarray,  # shape: (num_stocks, 240)
    max_lag: int = 30
) -> tuple[np.ndarray, np.ndarray]:
    """
    构建领先-滞后矩阵
    
    Returns:
        lag_matrix: (n, n) 时滞矩阵，lag_matrix[i,j] > 0 表示i领先j
        corr_matrix: (n, n) 相关系数矩阵
    """
    n = len(cluster_members)
    lag_matrix = np.zeros((n, n))
    corr_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            
            stock_i = cluster_members[i]
            stock_j = cluster_members[j]
            
            lag, corr = compute_tlcc(returns[stock_i], returns[stock_j], max_lag)
            
            lag_matrix[i, j] = lag
            corr_matrix[i, j] = corr
    
    return lag_matrix, corr_matrix
```

---

## 4. 龙头排序

### 4.1 PageRank方法

将领先-滞后关系转换为有向图，用PageRank算法排序。

```python
import networkx as nx

def rank_leaders_pagerank(
    cluster_members: list[int],
    lag_matrix: np.ndarray,
    corr_matrix: np.ndarray,
    min_lag: int = 3,  # 最小领先时间（分钟）
    min_corr: float = 0.3  # 最小相关系数
) -> list[tuple[int, float]]:
    """
    使用PageRank排序龙头
    
    Args:
        lag_matrix: 时滞矩阵
        corr_matrix: 相关系数矩阵
        min_lag: 最小领先时间（过滤噪音）
        min_corr: 最小相关系数（过滤弱相关）
    
    Returns:
        [(node_id, pagerank_score)] 按分数降序排列
    """
    n = len(cluster_members)
    
    # 构建有向图：箭头从领先者指向跟随者
    G = nx.DiGraph()
    
    for i in range(n):
        G.add_node(cluster_members[i])
    
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            
            lag = lag_matrix[i, j]
            corr = corr_matrix[i, j]
            
            # 筛选有效的领先关系
            if lag >= min_lag and corr >= min_corr:
                # i领先j，边从i指向j
                weight = corr * (lag / 30)  # 时滞越大，领先越明显
                G.add_edge(cluster_members[i], cluster_members[j], weight=weight)
    
    # 计算PageRank
    if len(G.edges()) == 0:
        # 无有效边，返回等权排序
        return [(m, 1.0 / n) for m in cluster_members]
    
    pagerank = nx.pagerank(G, weight='weight')
    
    # 按分数降序排列
    ranked = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
    
    return ranked
```

### 4.2 小样本替代方案

当Cluster成员数≤5时，PageRank区分度低，使用加权入度排序。

```python
def rank_leaders_weighted_indegree(
    cluster_members: list[int],
    lag_matrix: np.ndarray,
    corr_matrix: np.ndarray,
    min_lag: int = 3,
    min_corr: float = 0.3
) -> list[tuple[int, float]]:
    """
    加权入度排序（小样本替代方案）
    
    入度权重 = Σ(领先时间 × 相关系数)
    """
    n = len(cluster_members)
    scores = {}
    
    for i in range(n):
        total_lead_score = 0.0
        lead_count = 0
        
        for j in range(n):
            if i == j:
                continue
            
            lag = lag_matrix[i, j]
            corr = corr_matrix[i, j]
            
            if lag >= min_lag and corr >= min_corr:
                total_lead_score += lag * corr
                lead_count += 1
        
        scores[cluster_members[i]] = total_lead_score
    
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    return ranked
```

### 4.3 统一接口

```python
def identify_leader(
    cluster_members: list[int],
    returns: np.ndarray,
    max_lag: int = 30
) -> tuple[int, list[int]]:
    """
    识别Cluster龙头
    
    Returns:
        (leader_id, follower_ids)
    """
    n = len(cluster_members)
    
    # 构建领先-滞后矩阵
    lag_matrix, corr_matrix = build_lead_lag_matrix(
        cluster_members, returns, max_lag
    )
    
    # 选择排序方法
    if n <= 5:
        ranked = rank_leaders_weighted_indegree(
            cluster_members, lag_matrix, corr_matrix
        )
    else:
        ranked = rank_leaders_pagerank(
            cluster_members, lag_matrix, corr_matrix
        )
    
    leader = ranked[0][0]
    followers = [node for node, _ in ranked[1:]]
    
    return leader, followers
```

---

## 5. 分歧度监控

### 5.1 核心概念

Cluster内部的分歧度反映趋势阶段：
- **低分歧度**：成员走势趋同，处于合力期（买入信号）
- **高分歧度**：成员走势分化，处于瓦解期（卖出信号）

### 5.2 分歧度计算

$$Divergence = \frac{\sigma(returns)}{\overline{|returns|}}$$

```python
def compute_divergence(
    cluster_members: list[int],
    returns: np.ndarray,  # 当日收益率
    window: int = 30  # 滚动窗口（分钟）
) -> np.ndarray:
    """
    计算滚动分歧度
    
    Args:
        cluster_members: 成员节点ID
        returns: 分钟收益率矩阵 (num_stocks, 240)
        window: 滚动窗口大小
    
    Returns:
        分歧度序列（240-window+1维）
    """
    member_returns = returns[cluster_members, :]  # (n_members, 240)
    
    divergence = []
    
    for t in range(window, 240):
        window_returns = member_returns[:, t-window:t]
        
        # 窗口内累积收益
        cumulative = window_returns.sum(axis=1)
        
        # 分歧度 = 标准差 / 平均绝对值
        std = np.std(cumulative)
        mean_abs = np.mean(np.abs(cumulative))
        
        if mean_abs > 0:
            div = std / mean_abs
        else:
            div = 0.0
        
        divergence.append(div)
    
    return np.array(divergence)
```

### 5.3 趋势阶段判定

```python
def classify_trend_phase(
    divergence: float,
    prev_divergence: float = None
) -> str:
    """
    判定趋势阶段
    
    Returns:
        'formation': 建仓期/合力期
        'peak': 高峰期
        'dissolution': 瓦解期
        'neutral': 中性
    """
    if divergence < 0.3:
        return 'formation'  # 合力期 - 买入信号
    elif divergence > 0.7:
        return 'dissolution'  # 瓦解期 - 卖出信号
    elif prev_divergence is not None:
        if divergence > prev_divergence * 1.5:
            return 'dissolution'  # 分歧急剧上升
        elif divergence < prev_divergence * 0.7:
            return 'formation'  # 分歧收敛
    
    return 'neutral'
```

---

## 6. 信号输出

### 6.1 信号结构

遵循quant-strategy信号规范：

```python
@dataclass
class TickClusterSignal:
    stock_code: str
    direction: str  # 'BUY' / 'SELL' / 'HOLD'
    strength: float  # 信号强度 0-1
    price: float
    timestamp: datetime
    reason: str
    
    # 扩展信息
    cluster_id: int
    role: str  # 'leader' / 'follower'
    divergence: float
    trend_phase: str
```

### 6.2 信号生成规则

```python
def generate_signals(
    cluster: Cluster,
    leader: int,
    followers: list[int],
    divergence: float,
    trend_phase: str,
    stock_prices: dict[str, float]
) -> list[TickClusterSignal]:
    """
    生成交易信号
    """
    signals = []
    
    if trend_phase == 'formation':
        # 合力期：买入跟随股
        for follower in followers:
            code = cluster.members[follower]
            signals.append(TickClusterSignal(
                stock_code=code,
                direction='BUY',
                strength=0.7 - divergence,  # 分歧越低，信号越强
                price=stock_prices[code],
                timestamp=datetime.now(),
                reason=f"Cluster {cluster.cluster_id} 合力期，跟随龙头 {cluster.members[leader]}",
                cluster_id=cluster.cluster_id,
                role='follower',
                divergence=divergence,
                trend_phase=trend_phase
            ))
    
    elif trend_phase == 'dissolution':
        # 瓦解期：卖出所有持仓
        for member in cluster.members:
            signals.append(TickClusterSignal(
                stock_code=member,
                direction='SELL',
                strength=divergence - 0.3,  # 分歧越高，信号越强
                price=stock_prices[member],
                timestamp=datetime.now(),
                reason=f"Cluster {cluster.cluster_id} 瓦解期，获利了结",
                cluster_id=cluster.cluster_id,
                role='member',
                divergence=divergence,
                trend_phase=trend_phase
            ))
    
    return signals
```

---

## 7. 输出报告

### 7.1 Cluster报告格式

```markdown
## Cluster 7 - 半导体暗线

**识别日期**: 2026-02-04
**稳定性**: 0.72 (持续性热点)
**趋势阶段**: 合力期

### 成员
| 代码 | 名称 | 角色 | 领先时间 | 日涨幅 |
|------|------|------|----------|--------|
| 688001 | XX半导体 | 龙头 | - | +5.2% |
| 300123 | YY科技 | 跟随 | 8分钟 | +3.1% |
| 002456 | ZZ材料 | 跟随 | 12分钟 | +2.8% |

### 信号
- **买入**: 300123, 002456
- **信号强度**: 0.65
- **目标**: 跟随龙头688001
```

---

## 8. 参数配置

```yaml
lead_lag_analysis:
  # TLCC参数
  tlcc:
    max_lag: 30  # 最大时滞（分钟）
    min_lag: 3  # 最小有效时滞
    min_corr: 0.3  # 最小相关系数
    
  # 龙头排序
  leader_ranking:
    method_threshold: 5  # 成员数≤5使用加权入度
    
  # 分歧度
  divergence:
    window: 30  # 滚动窗口
    formation_threshold: 0.3  # 合力期阈值
    dissolution_threshold: 0.7  # 瓦解期阈值
    
  # 信号生成
  signal:
    min_strength: 0.3  # 最小信号强度
```

# 工程实现与性能优化

## 1. 概述

本文档描述策略的工程实现方案，解决计算复杂度、增量更新、并行计算等问题。

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         调度层                                   │
│              AcquisitionScheduler (15:30触发)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         计算层                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 特征计算器   │  │ DTW计算器    │  │ 聚类计算器   │          │
│  │ (8线程)     │  │ (16进程)    │  │ (单进程)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         存储层                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Redis       │  │ ClickHouse  │  │ 文件系统     │          │
│  │ (距离矩阵)   │  │ (Cluster)   │  │ (日志)       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 增量计算策略

### 3.1 问题分析

每日全量计算DTW复杂度过高：
- 5000×5000 = 2500万对
- 即使两阶段筛选后仍有约100万对需计算

### 3.2 增量更新方案

**核心思路**：只重新计算"行为发生显著变化"的股票。

```python
def detect_changed_stocks(
    today_features: np.ndarray,  # (num_stocks, 240)
    yesterday_features: np.ndarray,
    threshold: float = 0.5
) -> list[int]:
    """
    检测行为变化显著的股票
    
    变化度 = 今日向量与昨日向量的Euclidean距离
    """
    changed = []
    
    for i in range(len(today_features)):
        dist = np.linalg.norm(today_features[i] - yesterday_features[i])
        if dist > threshold:
            changed.append(i)
    
    return changed
```

### 3.3 增量更新流程

```python
async def incremental_update(
    date: str,
    redis_client,
    changed_stocks: list[int],
    all_stocks: list[int],
    features: np.ndarray
):
    """
    增量更新距离矩阵
    """
    # 1. 加载昨日距离矩阵
    yesterday_matrix = load_distance_matrix(redis_client, get_previous_date(date))
    
    # 2. 计算需要更新的股票对
    pairs_to_update = []
    for changed in changed_stocks:
        for other in all_stocks:
            if changed != other:
                pairs_to_update.append((min(changed, other), max(changed, other)))
    
    pairs_to_update = list(set(pairs_to_update))
    
    # 3. 重新计算变化的对
    new_distances = await compute_dtw_batch(features, pairs_to_update)
    
    # 4. 合并更新
    for (i, j), dist in new_distances.items():
        yesterday_matrix.add(i, j, dist)
    
    # 5. 存储
    save_distance_matrix(date, yesterday_matrix, redis_client)
```

### 3.4 更新策略选择

| 场景 | 策略 | 说明 |
|------|------|------|
| 交易日 | 增量更新 | 仅计算变化股票 |
| 每周一 | 全量更新 | 避免误差累积 |
| 参数调整 | 全量更新 | 参数变化需重算 |

---

## 4. 并行计算

### 4.1 特征计算并行化

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def compute_features_parallel(
    date: str,
    stock_codes: list[str],
    tick_data: dict[str, pd.DataFrame],
    num_workers: int = 8
) -> dict[str, np.ndarray]:
    """
    并行计算所有股票的特征向量
    """
    results = {}
    
    def compute_single(code):
        df = tick_data[code]
        return code, {
            'vector_a': build_vector_a(code, date, df),
            'vector_b': build_vector_b(code, date, df),
            'vector_c': build_vector_c(code, date, df),
        }
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, compute_single, code)
            for code in stock_codes
        ]
        
        for future in asyncio.as_completed(futures):
            code, features = await future
            results[code] = features
    
    return results
```

### 4.2 DTW计算并行化

使用进程池（绕过GIL）：

```python
from multiprocessing import Pool

def compute_dtw_chunk(args):
    """
    计算一个分片的DTW距离
    """
    vectors, pairs, window = args
    results = {}
    
    for i, j in pairs:
        dist = dtw_distance_with_window(vectors[i], vectors[j], window)
        results[(i, j)] = dist
    
    return results

def compute_dtw_parallel(
    vectors: np.ndarray,
    pairs: list[tuple[int, int]],
    window: int = 15,
    num_workers: int = 16,
    chunk_size: int = 10000
) -> dict[tuple[int, int], float]:
    """
    多进程并行计算DTW
    """
    # 分片
    chunks = [
        pairs[i:i+chunk_size] 
        for i in range(0, len(pairs), chunk_size)
    ]
    
    args_list = [(vectors, chunk, window) for chunk in chunks]
    
    # 并行执行
    with Pool(num_workers) as pool:
        results_list = pool.map(compute_dtw_chunk, args_list)
    
    # 合并结果
    all_results = {}
    for results in results_list:
        all_results.update(results)
    
    return all_results
```

### 4.3 Numba加速

```python
from numba import jit, prange

@jit(nopython=True, parallel=True)
def dtw_batch_numba(
    vectors: np.ndarray,  # (num_stocks, 240)
    pairs: np.ndarray,  # (num_pairs, 2)
    window: int
) -> np.ndarray:
    """
    Numba加速的批量DTW计算
    """
    num_pairs = len(pairs)
    results = np.zeros(num_pairs)
    
    for idx in prange(num_pairs):
        i, j = pairs[idx]
        results[idx] = dtw_distance_with_window(vectors[i], vectors[j], window)
    
    return results
```

---

## 5. 存储方案

### 5.1 Redis存储

**距离矩阵**（稀疏格式）：

```python
def save_distance_matrix_redis(
    date: str,
    matrix: SparseDistanceMatrix,
    redis_client
):
    """
    存储到Redis
    
    Key格式: dtw:{date}:{i}:{j}
    Value: 距离值
    
    使用Pipeline批量写入
    """
    pipe = redis_client.pipeline()
    
    for (i, j), dist in matrix.data.items():
        key = f"dtw:{date}:{i}:{j}"
        pipe.set(key, str(dist), ex=86400 * 7)  # 7天过期
    
    pipe.execute()
```

**特征向量**（用于增量计算）：

```python
def save_features_redis(
    date: str,
    stock_code: str,
    features: dict[str, np.ndarray],
    redis_client
):
    """
    存储特征向量到Redis
    """
    key = f"features:{date}:{stock_code}"
    value = {
        'vector_a': features['vector_a'].tolist(),
        'vector_b': features['vector_b'].tolist(),
        'vector_c': features['vector_c'].tolist(),
    }
    redis_client.set(key, json.dumps(value), ex=86400 * 7)
```

### 5.2 ClickHouse存储

**Cluster结果表**：

```sql
CREATE TABLE tick_clusters (
    date Date,
    cluster_id UInt32,
    members String,  -- 逗号分隔的股票代码
    leader_code String,
    avg_return Float64,
    avg_turnover Float64,
    correlation Float64,
    stability Float64,
    trend_phase String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, cluster_id);
```

**信号记录表**：

```sql
CREATE TABLE tick_cluster_signals (
    date Date,
    timestamp DateTime64(3),
    stock_code String,
    direction String,
    strength Float64,
    price Float64,
    cluster_id UInt32,
    role String,
    divergence Float64,
    trend_phase String,
    reason String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, timestamp, stock_code);
```

---

## 6. 异常处理

### 6.1 熔断机制

```python
class TickClusterCircuitBreaker:
    """
    计算任务熔断器
    """
    def __init__(
        self,
        failure_threshold: int = 3,
        timeout: int = 300,  # 5分钟
        recovery_timeout: int = 600  # 10分钟
    ):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.state = 'CLOSED'  # CLOSED / OPEN / HALF_OPEN
        self.last_failure_time = None
    
    async def execute(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerOpenError("熔断器开启中")
        
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs), 
                timeout=self.timeout
            )
            self.failure_count = 0
            self.state = 'CLOSED'
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.error(f"熔断器开启: {e}")
            
            raise
```

### 6.2 极端行情处理

```python
def detect_extreme_market(
    index_return: float,
    index_volatility: float
) -> bool:
    """
    检测极端行情
    
    触发条件：
    - 指数涨跌幅 > 3%
    - 或波动率 > 历史均值2倍
    """
    return abs(index_return) > 0.03 or index_volatility > HISTORICAL_VOL * 2

def handle_extreme_market(date: str):
    """
    极端行情下的处理策略
    """
    logger.warning(f"{date} 检测到极端行情，跳过Cluster分析")
    
    # 1. 标记该日数据为异常
    mark_date_as_extreme(date)
    
    # 2. 不生成信号
    return []
```

---

## 7. 监控与日志

### 7.1 性能指标

```python
class TickClusterMetrics:
    """
    性能监控指标
    """
    def __init__(self):
        self.feature_compute_time = 0.0
        self.dtw_compute_time = 0.0
        self.cluster_compute_time = 0.0
        self.total_stocks = 0
        self.total_pairs = 0
        self.num_clusters = 0
    
    def report(self) -> dict:
        return {
            "feature_compute_time_sec": self.feature_compute_time,
            "dtw_compute_time_sec": self.dtw_compute_time,
            "cluster_compute_time_sec": self.cluster_compute_time,
            "total_time_sec": self.feature_compute_time + self.dtw_compute_time + self.cluster_compute_time,
            "stocks_processed": self.total_stocks,
            "pairs_computed": self.total_pairs,
            "clusters_found": self.num_clusters,
            "pairs_per_second": self.total_pairs / self.dtw_compute_time if self.dtw_compute_time > 0 else 0,
        }
```

### 7.2 结构化日志

```python
import structlog

logger = structlog.get_logger()

def log_computation_complete(date: str, metrics: TickClusterMetrics):
    logger.info(
        "tick_cluster_computation_complete",
        date=date,
        **metrics.report()
    )
```

---

## 8. 配置

```yaml
engineering:
  # 增量计算
  incremental:
    enabled: true
    change_threshold: 0.5  # 变化检测阈值
    full_update_weekday: 1  # 周一全量更新
    
  # 并行计算
  parallel:
    feature_workers: 8
    dtw_workers: 16
    chunk_size: 10000
    use_numba: true
    
  # 存储
  storage:
    redis:
      host: "redis"
      port: 6379
      db: 2
      expire_days: 7
    clickhouse:
      host: "clickhouse"
      database: "quant"
      
  # 熔断
  circuit_breaker:
    failure_threshold: 3
    timeout_sec: 300
    recovery_sec: 600
    
  # 极端行情
  extreme_market:
    index_threshold: 0.03
    volatility_multiplier: 2.0
```

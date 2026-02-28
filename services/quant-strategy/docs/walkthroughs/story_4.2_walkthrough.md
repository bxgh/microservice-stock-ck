# Story 004.02 - 工程鲁棒性与分布式加速 (EngineeringPlus)

## 📌 背景
在 Story 004.01 中，我们已经打通了横截面回测仿真闭环。但每日从零开始计算 5000 只股票的 DTW 距离矩阵是一场浩大的算力消耗。本节将为这台量化引擎加装两层工程护盾——**增量缓存引擎**和**极端熔断器**——让其具备在生产环境下每日稳定运行的能力。

---

## 🏗️ 核心成就

### 1. 增量相似度引擎 (`IncrementalSimilarityEngine`)
通过"指纹比对"（欧氏距离测量近两日特征向量的差分），引擎将每日需要重算的 DTW 对数量**从全市场降至变动子集**，预期节省 50-80% 的算力开销：
- **指纹检测**: `_detect_changed_stocks()` 批量对比每只股票的昨日向量，精准圈出"行为发生剧变"的股票
- **局部重算**: 只对涉及变化股的股票对调用核心 DTW 计算
- **Redis 缓存**: 与 `RedisSparseCacheManager` 联动，把不变的配对距离从 Redis 直接复用

### 2. Redis 稀疏矩阵缓存 (`RedisSparseCacheManager`)
将 DTW 构建的稀疏矩阵以 Key-Value 格式落盘到 Redis：
- **批量 Pipeline 写入**：避免单条写入引发的 RTT 网络开销
- **对称键设计**：用 `sorted(s1, s2)` 确保 `(A,B)` 和 `(B,A)` 共享同一个缓存槽
- **指纹向量存储**：将个股当日特征向量以如 `json.dumps` 格式保存，供次日增量检测对比

### 3. 极端熔断器 (`TickClusterCircuitBreaker`)
实现标准化三态熔断（CLOSED→OPEN→HALF_OPEN→CLOSED）：
- **连续失败计步**: 若异步调用连续错误超过阈值 (默认3次)，自动切入 OPEN 态
- **动态恢复**: 超过冷却期后由 OPEN 降为 HALF_OPEN，允许探测性调用
- **手动拨断**: `manual_trip()` 支持外部行情异常（大盘暴跌）时主动切断信号生成

### 4. 统一性能日志 (`TickClusterMetrics`)
轻量级的指标抓拍器，记录 DTW 耗时、缓存命中率、股票数量等关键数据点以供 Grafana 展示。

---

## 📁 核心文件
- **增量引擎**: [incremental_engine.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/analysis/similarity/incremental_engine.py)
- **稀疏缓存**: [redis_sparse_cache.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/cache/redis_sparse_cache.py)
- **熔断器**: [circuit_breaker.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/utils/circuit_breaker.py)
- **性能指标**: [metrics.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/utils/metrics.py)
- **熔断测试**: [test_circuit_breaker.py](file:///home/bxgh/microservice-stock/services/quant-strategy/tests/utils/test_circuit_breaker.py)
- **增量测试**: [test_incremental_engine.py](file:///home/bxgh/microservice-stock/services/quant-strategy/tests/analysis/test_incremental_engine.py)

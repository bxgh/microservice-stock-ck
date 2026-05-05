# Story Implementation Plan

**Story ID**: 003.01
**Story Name**: 两阶段相似度计算引擎 (SimilarityEngine)
**开始日期**: 2026-02-25
**预期完成**: 2026-02-26
**负责人**: Antigravity
**AI模型**: Claude 4.5 Sonnet / o1 (算法设计)

---

## 📋 Story概述

### 目标
在可接受的时间内（<60分钟）完成全市场股票的分笔数据特征向量（240维）配对相似度计算，解决计算复杂度爆炸问题。通过 欧几里得降维粗筛 + Sakoe-Chiba 窗口约束的 DTW 精算，最终合成代表多维特征的关联权重，服务下游的“资金团”聚类。

### 验收标准
- [ ] 全市场 5000 只股票对应约 1250 万对组合，双阶段计算完成时间 < 60 分钟。
- [ ] 成功调用 Euclidean 算法将全市场候选对筛减到 5% (约 62.5 万对)。
- [ ] 成功使用带有 15 分钟窗口约束的动态时间扭曲 (DTW) 算法。
- [ ] 将多维特征（向量 A 主动买入、向量 B 盘口失衡、向量 C 收益率）进行归一化后加权合成。
- [ ] 并发安全性与健壮性：支持错误重试和进度恢复。

### 依赖关系
- **外部依赖**: Redis (用于缓存中间向量与最终进度), ClickHouse (读取原始 Tick/Kline 特征数据)。
- **前置依赖**: Epic-002 Part 1 (向量 A/B/C 输出的 Redis FeatureStore)。

---

## 🎯 需求分析

### 功能需求
1. 两阶段计算结构：欧式距离粗筛出 Top N，DTW 计算剩余配对的准确距离。
2. 距离值加权融合：根据各个特征矩阵进行标准化融合。
3. 高可用：提供运行进度观察借口和存储策略 (Redis 缓存计算结果)。

### 非功能需求
- **性能要求**: 全流程单日数据耗时 < 60 分钟（48核测试基准）。
- **并发要求**: 利用 Python 多进程机制处理 CPU 密集型任务。
- **内存要求**: 所有序列加载至内存后不可发生 OOM (控制批处理大小)。

---

## 🏗️ 技术设计

### 架构设计

```mermaid
graph TD
    Redis[Redis Feature Store] --> EEngine[Euclidean预筛引擎]
    EEngine --Top 5% 组合--> TaskQ[Task Queue (可分块分配)]
    TaskQ --> W1((Worker 1 - Numba DTW))
    TaskQ --> W2((Worker N - Numba DTW))
    W1 --> Merger[Results Merger & Normalization]
    W2 --> Merger
    Merger --> SimMatrix[稀疏距离矩阵]
    SimMatrix --> Graph[Adjacency Matrix Generator]
```

### 核心组件

#### 组件1: `DTWCore` (src/analysis/similarity/dtw_core.py)
**职责**: 使用 Numba 实现高性能底层动态时间扭曲运算。

**接口设计**:
```python
import numpy as np
from numba import njit

@njit(fastmath=True)
def dtw_distance_with_window(series_a: np.ndarray, series_b: np.ndarray, window: int = 15) -> float:
    """带 Sakoe-Chiba 窗口约束的 DTW 动态规划机器码
    
    Args:
        series_a: 1D 数组序列A
        series_b: 1D 数组序列B
        window: 最大扭曲步数 (默认 15)
    
    Returns:
        float: 最小扭曲距离
    """
    pass
```

**并发安全**: 无副作用的纯函数，多进程并发下绝对安全。

#### 组件2: `SimilarityEngine` (src/analysis/similarity/engine.py)
**职责**: 编排两阶段算法并利用 `ProcessPoolExecutor` 实现多核打满。

**并发安全**:
```python
# 示例：采用 asyncio 控制下的进程池安全派发
import asyncio
from concurrent.futures import ProcessPoolExecutor

class SimilarityEngine:
    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        
    async def compute_similarity_all(self, features: dict) -> list:
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=self.max_workers) as pool:
            # Chunking logic...
            tasks = [
                loop.run_in_executor(pool, process_dtw_chunk, chunk) 
                for chunk in chunks
            ]
            results = await asyncio.gather(*tasks)
        return results
```

---

## 📁 文件变更

### 新增文件
- [ ] `src/analysis/similarity/__init__.py` - 模块初始化
- [ ] `src/analysis/similarity/dtw_core.py` - Numba JIT 优化算法核心
- [ ] `src/analysis/similarity/euclidean_filter.py` - 第一阶段批处理过滤工具
- [ ] `src/analysis/similarity/engine.py` - 主并发控制引擎
- [ ] `src/core/models/similarity_matrix.py` - 输出数据结构
- [ ] `tests/analysis/similarity/test_dtw_core.py` - 单元测试
- [ ] `tests/analysis/similarity/test_similarity_engine.py` - 引擎集成与并发测试

---

## 🔄 实现计划

### Phase 1: 核心逻辑实现
**预期时间**: 1.5 天
- [ ] 编写 Numba DTW 算法并验证正确性。
- [ ] 编写 Euclidean pre-filter 并行计算。
- [ ] 验证 3 维度特征的 Numpy 数组加权逻辑。

### Phase 2: 测试实现
**预期时间**: 0.5 天
- [ ] 编写含时差的波形数据，测试 DTW 对于滞后/领先对齐的敏锐度。
- [ ] 并发进程池安全运行测试。
- [ ] 性能压测。

### Phase 3: 质量检查
**预期时间**: 0.2 天
- [ ] 修复代码风格、类型校验，确保 Ruff, Mypy 100% 达标。

---

## ⚙️ 技术细节

### 并发安全设计
因 DTW 计算属重度 CPU 密集型运算，不可基于协程(Asyncio)并发。必须使用进程池隔离。内存层面利用 numpy 的 `np.memmap` 或者精细 chunk 划定来避免内存峰值溢出。

### 错误处理策略
- 捕获 `TimeoutError` 等资源异常并重启对应的 Chunk worker。
- 保留未成功的 Chunk，方便后续断点恢复。

### 性能优化
- `@njit(fastmath=True)`: 关闭严格浮点检查，利用机器级向量优化大幅提速。
- SciPy C 核心调用: 第一阶段 Euclidean 使用 `scipy.spatial.distance.pdist` C 扩展计算，比纯 python 循环快数千倍。

---

## 🧪 测试策略

### 单元测试覆盖
- [ ] 测试两个完全波峰偏移的波形的 DTW 相似度 > Euclidean 相似度。
- [ ] 验证 window 参数正确截断大跨度畸变。

### 性能测试
- [ ] Mock 出 100x100 的 240D 向量，评估 CPU 核利用率与计算用时，估算全集耗时。

---

## ✅ 完成检查清单

### 设计确认
- [x] Phase 1: 生成 Implementation Plan

*(其他项在开发与审核过程中勾选)*

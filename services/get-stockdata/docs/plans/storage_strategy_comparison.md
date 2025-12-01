# 高频快照数据存储方案对比分析

## 1. 核心对比：Parquet vs ClickHouse

### 1.1 Parquet 文件存储（当前方案）

**优势**:
- ✅ **零依赖**: 无需额外服务，文件系统即可
- ✅ **极高性能**: 列式存储，读取速度是 CSV 的 10-50 倍
- ✅ **完美压缩**: Gzip 压缩后体积是 CSV 的 1/10
- ✅ **生态成熟**: Pandas, Spark, Dask 原生支持
- ✅ **数据不变性**: 文件一旦写入，天然支持审计和追溯
- ✅ **分布式友好**: 文件可以直接复制到对象存储（S3/OSS）

**劣势**:
- ❌ **查询不灵活**: 需要加载整个文件或分区才能查询
- ❌ **无索引**: 按股票代码、时间点查询效率低
- ❌ **更新困难**: 无法Update，只能追加或重写
- ❌ **并发写入**: 同一文件不支持多进程同时写入

**最佳场景**:
- 批量分析（回测、特征工程）
- 数据归档（长期存储）
- 离线计算（Spark/Dask）

---

### 1.2 ClickHouse 数据库存储

**优势**:
- ✅ **实时查询**: SQL 查询，亚秒级响应
- ✅ **灵活索引**: 可按股票代码、时间建立索引
- ✅ **高并发**: 支持多客户端同时读写
- ✅ **聚合强大**: 内置 VWAP、分位数等金融计算函数
- ✅ **数据去重**: MergeTree 引擎自动去重
- ✅ **实时更新**: 支持删除和更新（虽然不推荐）

**劣势**:
- ❌ **资源消耗**: 需要额外的内存和磁盘（建议 8GB+ RAM）
- ❌ **运维成本**: 需要管理数据库、备份、监控
- ❌ **学习曲线**: 需要学习 SQL 和 ClickHouse 特性
- ❌ **单机扩展性**: 超过 TB 级需要集群

**最佳场景**:
- 实时查询（监控看板、API 服务）
- 交互式分析（数据探索）
- 复杂聚合（多维分析）

---

## 2. 针对您场景的专家建议

### 2.1 当前需求分析
根据今天的讨论，您的核心需求是：
1. **采集**：高频快照采集（3秒/轮）
2. **存储**：长期保存盘口数据
3. **分析**：未来做量化研究（主动买卖、OFI、VWAP）

### 2.2 推荐策略：**Parquet 优先，ClickHouse 可选**

**阶段 1（当前 - 3个月）：Parquet 单兵模式**
- **理由**：
  - 您刚开始积累数据，总量还不大（预计 3个月 < 100 GB）。
  - Parquet 的 Pandas/NumPy 生态对量化研究极其友好。
  - 无需运维数据库，专注于数据质量。

- **行动**：
  - 继续使用当前的 ParquetWriter。
  - 每天一个目录，按小时分文件。
  - 一个月后做一次性能压测（查询速度）。

**阶段 2（3-6个月）：Parquet + ClickHouse 双轨**
- **触发条件**：
  - 数据总量 > 100 GB。
  - 出现"需要快速查询某只股票某个时刻的盘口"的需求。
  - 需要构建实时监控看板。

- **行动**：
  - **Parquet** 作为冷数据归档（3个月以前的数据）。
  - **ClickHouse** 作为热数据查询（最近 3 个月）。
  - 编写定时任务，将 Parquet 数据导入 ClickHouse。

---

## 3. 混合存储架构（推荐）

```
实时采集层
  ↓
ParquetWriter (原始数据落盘，3秒/轮)
  ↓
  ├─→ /data/snapshots/YYYYMMDD/*.parquet  (冷数据，永久保存)
  │
  └─→ ClickHouse (热数据，近3月)
      └─→ 表结构：snapshot_hot
          - 自动分区按日期
          - 索引：(stock_code, snapshot_time)
```

### 3.1 ClickHouse 表结构建议

```sql
CREATE TABLE snapshot_hot (
    snapshot_time DateTime64(3),  -- 毫秒精度（虽然当前只有秒）
    stock_code String,
    price Float64,
    bid1 Float64,
    bid_vol1 UInt32,
    ask1 Float64,
    ask_vol1 UInt32,
    bid2 Float64,
    bid_vol2 UInt32,
    ask2 Float64,
    ask_vol2 UInt32,
    -- ... bid3-bid5, ask3-ask5
    volume UInt64,
    INDEX idx_stock stock_code TYPE bloom_filter GRANULARITY 1
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(snapshot_time)
ORDER BY (stock_code, snapshot_time)
SETTINGS index_granularity = 8192;
```

### 3.2 数据流转策略

**每日凌晨 02:00**:
1. 将昨天的 Parquet 文件导入 ClickHouse（增量导入）。
2. 删除 ClickHouse 中 90 天前的数据（释放空间）。
3. Parquet 文件永久保留（作为唯一真实数据源）。

---

## 4. 决策树

**您应该什么时候引入 ClickHouse？**

```
是否需要实时查询（秒级响应）？
├─ 否 → 继续使用 Parquet ✅
├─ 是 → 
    ├─ 数据量 < 50 GB？
    │   ├─ 是 → Parquet + DuckDB（轻量级 OLAP）
    │   └─ 否 → Parquet + ClickHouse
    └─ 需要构建 Web 看板？
        └─ 是 → 必须 ClickHouse
```

---

## 5. 当前行动建议

### 立即行动（本周）
- ✅ **保持 Parquet 方案**：经过验证，运行稳定。
- ✅ **积累数据**：先跑 1-2 周，积累足够样本。

### 观察期（2-4 周）
- 📊 **性能测试**：
  - 测试从 Parquet 中查询"600000 在 2025-11-28 14:30 的盘口"需要多久。
  - 如果 < 1 秒，Parquet 够用。
  - 如果 > 5 秒，考虑 ClickHouse。

### 条件触发（未来）
如果出现以下需求，立即引入 ClickHouse：
- 需要实时监控看板（如"当前异动的前10只股票"）。
- 需要提供 API 服务（其他系统查询盘口数据）。
- 量化策略需要频繁回查历史盘口。

---

## 6. 对比总结表

| 维度 | Parquet | ClickHouse | 推荐 |
|------|---------|------------|------|
| **写入速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Parquet（批量写入更快） |
| **查询速度（单条）** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ClickHouse |
| **查询速度（批量）** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Parquet（Spark/Dask） |
| **资源消耗** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Parquet |
| **运维成本** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Parquet |
| **数据安全** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Parquet（文件不变性） |
| **实时性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ClickHouse |
| **SQL支持** | ❌ | ✅ | ClickHouse |

---

## 7. 最终建议

**当前阶段（0-3个月）**:
> **保持 Parquet 方案**。专注于数据质量和采集稳定性，暂不引入 ClickHouse。

**理由**:
1. 数据量还小，Parquet 完全够用。
2. 量化研究的主力工具（Pandas, NumPy）与 Parquet 完美匹配。
3. 避免过早优化，减少运维负担。

**后续扩展（3个月后）**:
> 如果需要实时监控或 API 服务，再引入 ClickHouse 作为热数据查询层。Parquet 永远是唯一的真实数据源（Single Source of Truth）。

---

**您觉得这个策略是否合理？**

# 01 架构设计：全市场分布式分片采集

## 1. 分片策略 (Distributed Sharding)
为了解决单机采集全市场 5,800+ 股票造成的网络 IO 和主线程阻塞问题，系统采用基于 Redis 的动态分片方案。

### 分片基础
*   **分片算法**: `xxHash64(stock_code) % Total_Shards`
*   **分片数量**: 目前设置为 3
*   **分片存储**: Node 41 Redis `metadata:stock_codes:shard:{index}`

### 负载分布 (实测)
| 分片 ID | 机器节点 | 股票数量 | 特点 |
|---|---|---|---|
| Shard 0 | Node 41 | 1,942 | 包含上证 60 段主要蓝筹 |
| Shard 1 | Node 58 | 1,925 | 包含深证 00/30 段成长股 |
| Shard 2 | Node 111 | 1,934 | 包含北交所及其他段 |

---

## 2. 数据流向

### 采集层 (Collector Layer)
每个节点的 `intraday-tick-collector` 容器通过环境变量 `SHARD_INDEX` 确定自己的身份，启动时连接中心 Redis 领取任务清单。详情见 [Mootdx-API 集成 (06_MOOTDX_API_INTEGRATION.md)](06_MOOTDX_API_INTEGRATION.md)。

### 传输层 (Transport Layer)
*   **本地写入**: 使用 `asynch` 异步池连接本地/主 ClickHouse。
*   **代理透传**: Node 58/111 通过内网代理访问中心数据库。

### 存储层 (Storage Layer)
*   **ClickHouse**: `tick_data_intraday` 表采用 MergeTree 引擎，按 `trade_date` 分区，按 `(trade_date, stock_code)` 排序。

---

## 3. 动态加载逻辑
`IntradayTickCollector` 类实现了一个智能加载器：
1.  **单机模式** (`SHARD_TOTAL=1`): 从本地 YAML 文件读取（如 HS300 特定池）。
2.  **分布式模式** (`SHARD_TOTAL>1`): 自动连接 Redis 获取对应索引的 SET 成员。

---

## 4. 主机名区分 (Host Visibility)
每个采集器容器被赋予了独立的主机名：
*   `node-41-collector`
*   `node-58-collector`
*   `node-111-collector`
这确保了即使汇总到同一个数据库，开发者也能通过 `SELECT hostName()` 审计数据来源。

---

## 5. 自愈层 (Self-Healing Layer)
为了应对分布式采集中的瞬时故障，系统集成了自动校验与补采机制。详情见 [数据校验 (08_INTRADAY_VALIDATION.md)](08_INTRADAY_VALIDATION.md)。
- **全局校验**: 定时对比预期总数与分布式表实际总数。
- **靶向修复**: 仅补采缺失部分，并重新通过分布式表分发。

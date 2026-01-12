# microservice-stock 架构文档

> **更新时间**: 2026-01-09  
> **当前架构**: 3-Shard 高性能并行集群 (Server 41/58/111)

---

## 🏗️ 架构概览 (v3.0)

本项目采用 **3节点全并行分片架构**，旨在最大化数据采集与即时分析的吞吐量。

```mermaid
graph TD
    Client[客户端/应用] -->|写入/查询| CK_Dist[ClickHouse 分布式表]
    Client -->|缓存读写| Redis_Cls[Redis Cluster]

    subgraph "Server 41 (Shard 1)"
        CK_1[ClickHouse Node 1]
        Redis_1[Redis Master 1]
        Worker_1[gsd-worker 1]
    end

    subgraph "Server 58 (Shard 2)"
        CK_2[ClickHouse Node 2]
        Redis_2[Redis Master 2]
        Worker_2[gsd-worker 2]
    end

    subgraph "Server 111 (Shard 3)"
        CK_3[ClickHouse Node 3]
        Redis_3[Redis Master 3]
        Worker_3[gsd-worker 3]
    end

    CK_Dist -.->|自动分片| CK_1
    CK_Dist -.->|自动分片| CK_2
    CK_Dist -.->|自动分片| CK_3

    Redis_Cls -.->|Slot 0-5460| Redis_1
    Redis_Cls -.->|Slot 5461-10922| Redis_2
    Redis_Cls -.->|Slot 10923-16383| Redis_3
```

### 核心特性
- **ClickHouse**: 3-Shard 无副本架构 (Shard 01/02/03)，数据按 `stock_code` Hash 分片。
- **Redis**: 3-Master 集群 (Port 16379)，Slots 平均分配。
- **并行计算**: 3个 Worker 节点并行处理，性能提升 300%。

---

## 📚 文档索引

### 基础设施 (`infrastructure/`)

| 文档 | 说明 | 状态 |
|------|------|------|
| [clickhouse-3shard-cluster.md](infrastructure/clickhouse-3shard-cluster.md) | ClickHouse 3分片架构详解 | ✅ v3.0 |
| [redis-3shard-cluster.md](infrastructure/redis-3shard-cluster.md) | Redis 3分片架构详解 | ✅ v3.0 |
| [server-hardware.md](infrastructure/SERVER_HARDWARE_ARCHITECTURE.md) | 服务器硬件架构 | ✅ v3.0 |
| [server-111-network.md](infrastructure/SERVER_111_NETWORK_CONFIG.md) | Server 111 三网卡配置详解 | ✅ v3.1 |
| [verified-tdx-hosts.md](infrastructure/VERIFIED_TDX_HOSTS_20260111.md) | 已验证的 TDX 节点列表 | ✅ v3.1 |
| [tdx-docker-config.md](data_acquisition/TDX_POOL_DOCKER_CONFIG.md) | Mootdx 容器部署指南 | ✅ v3.1 |

### 数据采集 (`data_acquisition/`)

| 文档 | 说明 | 状态 |
|------|------|------|
| [mootdx-api-diagnostic.md](data_acquisition/DIAGNOSTIC_TOOLS.md) | TDX 连接池诊断工具说明 | ✅ 新增 |

### 业务架构 (`services/`)

| 文档 | 说明 | 状态 |
|------|------|------|
| [tick_data_sharding_implementation.md](tick_data_sharding_implementation.md) | 分笔数据分布式 Sharding 实现 | ✅ v3.0 |


---

## 📋 相关文档

| 类型 | 位置 |
|------|------|
| 运维文档 | [docs/operations/](../operations/) |
| AI 上下文 | [docs/ai_context/](../ai_context/) |
| 进度报告 | [docs/reports/](../reports/) |

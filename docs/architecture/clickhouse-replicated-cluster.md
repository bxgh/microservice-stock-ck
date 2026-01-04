# 架构：ClickHouse 双主复制集群 (Active-Active)

## 1. 概述
股票数据系统采用 **多主 (Active-Active)** ClickHouse 集群架构，部署在两台物理服务器（Server 41 和 Server 58）上。该架构确保了高可用性 (HA) 和实时数据一致性，允许向任一节点写入数据并自动同步到另一节点。

## 2. 集群拓扑

```mermaid
graph TD
    subgraph Cluster ["ClickHouse 集群 (stock_cluster)"]
        node41["Server 41 (副本 1)"]
        node58["Server 58 (副本 2)"]
    end

    subgraph Coordination ["协调层 (嵌入式 Keeper)"]
        keeper41["Keeper 41 (ID: 1, Leader)"]
        keeper58["Keeper 58 (ID: 2, Follower)"]
    end

    node41 <-->|数据同步 (端口 9009)| node58
    node41 ---|元数据| keeper41
    node58 ---|元数据| keeper58
    keeper41 <-->|Raft 共识 (端口 9234)| keeper58
```

## 3. 服务器角色与关系

在双主架构中，两台服务器在 ClickHouse 数据层面是**对等**的，但在 Keeper 协调层面有明确的主从角色：

### 3.1 Server 41 (192.168.151.41)
- **数据角色**: 副本 1 (Replica 1)。承载全量业务数据，支持读写。
- **协调角色**: **Keeper Leader**。作为分布式协调服务的领导者，负责处理所有元数据变更请求的排序。
- **网络职责**: 提供主 HTTP/TCP 接口供本地服务调用。

### 3.2 Server 58 (192.168.151.58)
- **数据角色**: 副本 2 (Replica 2)。承载全量业务数据，与 41 实时同步，支持读写。
- **协调角色**: **Keeper Follower**。参与 Raft 选举和数据确认，当 41 宕机时可参与选举成为新 Leader（需扩容至 3 节点以实现自动切换）。
- **网络职责**: 作为 41 的热备节点，同时分担本地采集服务的写入压力。

### 3.3 交互逻辑
1. **双向同步**: 任意节点的数据写入都会生成一个 Log Entry 写入 Keeper 队列，另一节点感知后通过 9009 端口拉取数据块。
2. **主动-主动 (Active-Active)**: 两个节点同时处于在线状态，均可接受客户端连接。
3. **故障恢复**: 若任一节点故障，另一节点保持运行；故障节点恢复后会自动追平数据差异。

## 4. 通信与端口


| 端口 | 协议 | 说明 |
| :--- | :--- | :--- |
| **8123** | HTTP | 客户端接口、Grafana 以及常规查询。 |
| **9000** | TCP | 高性能查询和 `clickhouse-client` 使用的原生协议。 |
| **9009** | HTTP | **服务器间同步端口**。用于副本间的数据块传输，至关重要。 |
| **9181** | Keeper | ClickHouse 与 Keeper 之间的客户端通信端口。 |
| **9234** | Raft | Keeper 节点之间 Raft 共识协议的通信端口。 |

## 4. 配置详情

### 4.1 ClickHouse Keeper (嵌入式)
作为外部 ZooKeeper 的替代方案，嵌入式 Keeper 负责管理复制队列和元数据一致性。
- **配置文件**: `/etc/clickhouse-server/config.d/keeper_config.xml`
- **仲裁机制**: 2 节点（至少需要 1 个节点存活才能保证集群可写；2 节点提供基础冗余，建议未来扩容至 3 节点以防脑裂）。

### 4.2 复制宏定义 (Macros)
为了支持标准化的建表语句，每台主机通过宏定义了所属的 `shard` 和 `replica` 名称：

| 服务器 | Shard | Replica |
| :--- | :--- | :--- |
| **41** | `01` | `server41` |
| **58** | `01` | `server58` |

### 4.3 网络识别
ClickHouse 在 `replication_config.xml` 中配置了 `interserver_http_host`，确保节点间通过固定 IP 而非不稳定的主机名进行识别：
- Server 41: `192.168.151.41`
- Server 58: `192.168.151.58`

## 5. 存储引擎与迁移标准
所有需要同步的业务表必须使用 `Replicated` 系列引擎。

### 5.1 ReplicatedReplacingMergeTree
用于需要去重的表（如 K线数据、股票基本信息）。
```sql
ENGINE = ReplicatedReplacingMergeTree(
    '/clickhouse/tables/{shard}/TABLE_NAME', 
    '{replica}', 
    [version_column]
)
```

### 5.2 ReplicatedMergeTree
用于高频时序数据（如 分笔数据 Tick Data）。
```sql
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/TABLE_NAME', 
    '{replica}'
)
```

## 6. 运维指南
- **写入操作**: 负载可以均衡分配到两个节点，`Replicated` 引擎会根据版本列自动处理冲突。
- **容灾恢复**: 若一个节点宕机，另一节点继续提供服务。节点恢复后，会自动从存活节点拉取缺失的数据块（Log Entries）。
- **状态监控**: 定期检查 `system.replicas` 表中的 `is_readonly` 或 `is_session_expired` 标志。

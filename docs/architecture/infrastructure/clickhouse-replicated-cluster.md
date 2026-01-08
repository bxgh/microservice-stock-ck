# 架构：ClickHouse 多主复制集群 (Active-Active)

## 1. 概述
股票数据系统采用 **多主 (Active-Active)** ClickHouse 集群架构，当前生产环境部署在三台物理服务器（Server 41、Server 58 和 Server 111）上，组成了 **3节点高可用集群**。该架构实现了真正的高可用性 (HA) 和防脑裂 (Split-Brain) 能力，允许向任一节点写入数据并自动同步到其他所有节点。

> 💡 **扩容记录**: 3节点扩容已于 2026-01-07 完成。详见 [ClickHouse 3节点扩容方案](file:///home/bxgh/microservice-stock/docs/operations/CLICKHOUSE_3NODE_EXPANSION.md)

## 2. 集群拓扑

```mermaid
graph TD
    subgraph Cluster ["ClickHouse 集群 (stock_cluster)"]
        node41["Server 41 (副本 1)"]
        node58["Server 58 (副本 2)"]
        node111["Server 111 (副本 3)"]
    end

    subgraph Coordination ["协调层 (嵌入式 Keeper)"]
        keeper41["Keeper 41 (ID: 1, Follower)"]
        keeper58["Keeper 58 (ID: 2, Leader)"]
        keeper111["Keeper 111 (ID: 3, Follower)"]
    end

    %% 数据同步 (Mesh)
    node41 <-->|数据同步 (9009)| node58
    node58 <-->|数据同步 (9009)| node111
    node111 <-->|数据同步 (9009)| node41

    %% 元数据连接
    node41 ---|元数据| keeper41
    node58 ---|元数据| keeper58
    node111 ---|元数据| keeper111

    %% Raft 共识
    keeper41 <-->|Raft (9234)| keeper58
    keeper58 <-->|Raft (9234)| keeper111
    keeper111 <-->|Raft (9234)| keeper41
```

## 3. 服务器角色与关系

在三主架构中，三台服务器在 ClickHouse 数据层面是**完全对等**的，均持有全量数据副本。在 Keeper 协调层面，通过 Raft 协议选举产生一个 Leader 和两个 Follower。

### 3.1 Server 41 (192.168.151.41)
- **数据角色**: 副本 1 (Replica 1)。
- **协调角色**: **Keeper Follower** (当前状态，可能随选举变化)。
- **网络职责**: 承载部分读写流量。

### 3.2 Server 58 (192.168.151.58)
- **数据角色**: 副本 2 (Replica 2)。
- **协调角色**: **Keeper Leader** (当前状态，负责处理所有元数据变更请求的排序)。
- **网络职责**: 承载部分读写流量。

### 3.3 Server 111 (192.168.151.111)
- **数据角色**: 副本 3 (Replica 3)。作为扩容节点加入，持有全量数据。
- **协调角色**: **Keeper Follower**。
- **网络职责**: 增强集群的读取能力和容灾能力。

### 3.4 交互逻辑
1. **多向同步**: 任意节点的数据写入都会生成 Log Entry，其他两个节点通过 9009 端口异步拉取并合并数据。
2. **高可用性**: 集群可容忍 **1个节点** 宕机而不影响读写服务（Raft Quorum = 2/3）。
3. **防脑裂**: 3节点架构消除了2节点架构中网络分区导致的数据不一致风险。

## 4. 通信与端口

| 端口 | 协议 | 说明 |
| :--- | :--- | :--- |
| **8123** | HTTP | 客户端接口、Grafana 以及常规查询。 |
| **9000** | TCP | 高性能查询和 `clickhouse-client` 使用的原生协议。 |
| **9009** | HTTP | **服务器间同步端口**。用于副本间的数据块传输。 |
| **9181** | Keeper | ClickHouse 与 Keeper 之间的客户端通信端口。 |
| **9234** | Raft | Keeper 节点之间 Raft 共识协议的通信端口。 |

## 5. 配置详情

### 5.1 ClickHouse Keeper (嵌入式)
- **配置文件**: `/etc/clickhouse-server/config.d/keeper_config.xml`
- **仲裁机制**: **3 节点**。Quorum 为 2，即至少需要 2 个 Keeper 节点存活才能进行元数据变更（如 DDL、数据块写入）。
- **动态重配置**: 已启用 `reconfig` 命令，允许在不重启集群的情况下动态添加或移除 Keeper 节点。

### 5.2 复制宏定义 (Macros)
每台主机在 `/etc/clickhouse-server/config.d/replication_config.xml` 中定义了身份：

| 服务器 | Shard | Replica |
| :--- | :--- | :--- |
| **41** | `01` | `server41` |
| **58** | `01` | `server58` |
| **111** | `01` | `server111` |

### 5.3 网络识别
配置了 `interserver_http_host` 为各节点的固定业务 IP：
- Server 41: `192.168.151.41`
- Server 58: `192.168.151.58`
- Server 111: `192.168.151.111`

## 6. 存储引擎与迁移标准
所有需要同步的业务表必须使用 `Replicated` 系列引擎。

### 6.1 ReplicatedReplacingMergeTree
用于需要去重的表（如 K线数据、股票基本信息）。
```sql
ENGINE = ReplicatedReplacingMergeTree(
    '/clickhouse/tables/{shard}/TABLE_NAME', 
    '{replica}', 
    [version_column]
)
```

### 6.2 ReplicatedMergeTree
用于高频时序数据（如 分笔数据 Tick Data）。
```sql
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/TABLE_NAME', 
    '{replica}'
)
```

## 7. 运维指南
- **状态监控**: 定期检查 Keeper 集群状态 (`echo mntr | nc localhost 9181`) 和 ClickHouse 副本状态 (`system.replicas`)。
- **故障恢复**: 
    - **1 节点故障**: 集群正常读写，无人工干预。节点恢复后自动追平数据。
    - **2 节点故障**: 集群进入只读模式或不可用（取决于剩余节点是否是 Leader）。需尽快恢复至少 1 个故障节点以满足 Quorum。
- **扩缩容**: 使用 `reconfig` 命令进行动态扩缩容。

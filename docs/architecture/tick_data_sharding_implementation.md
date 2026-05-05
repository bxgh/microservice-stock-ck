# 分笔数据分布式分片实现总结 (Tick Data Distributed Sharding Implementation)

## 1. 概述 (Overview)

为了支持高频和大量分笔数据采集（约 5000 只股票 * 每日分笔数据），我们实施了 **分布式分片架构**。该架构确保数据采集工作负载在 3 台服务器（Server 41, 58, 111）之间负载均衡，使用统一的股票列表和一致性哈希策略。

## 2. 架构组件 (Architecture Components)

### 2.1. 基础设施
- **Server 41 (Orchestrator Node)**: 运行 `task-orchestrator`，Redis Cluster，并处理 **Shard 0**。
- **Server 58 (Worker Node)**: 远程工作节点，处理 **Shard 1**。
- **Server 111 (Worker Node)**: 远程工作节点，处理 **Shard 2**。
- **Redis Cluster**: 作为元数据和任务分配的中心协调点。

### 2.2. 服务
- **gsd-worker**: 执行数据采集的核心工作服务。
- **task-orchestrator**: 调度每日股票列表采集并触发 Shard 0。
- **mootdx-api**: 为所有节点提供统一的 TDX 服务器网关。

## 3. 分片逻辑与数据流 (Sharding Logic & Data Flow)

分片过程包含两个主要阶段：**准备阶段** 和 **执行阶段**。

### 阶段 1: 准备 (每日股票代码采集)
**时间**: 每日 09:05
**服务**: `daily_stock_collection.py` (通过 Orchestrator 在 Server 41 运行)

1.  **获取**: 从配置的云端 API 获取 A 股全量股票列表。
2.  **分片计算**:
    *   使用 **xxHash64** 算法对股票代码（例如 "000001.SZ"）进行计算，以确保高性能和均匀分布。
    *   公式: `shard_id = xxhash.xxh64(code).intdigest() % 3`
    *   该算法与 ClickHouse Distributed 表使用的分片策略匹配，确保尽可能的数据本地性 (Data Locality)。
3.  **存储至 Redis**:
    *   将分片后的列表写入 Redis Sets。
    *   **Keys**: `metadata:stock_codes:shard:0`, `metadata:stock_codes:shard:1`, `metadata:stock_codes:shard:2`。
    *   **TTL**: 25 小时。

### 阶段 2: 执行 (分布式采集)
**时间**: 每日 16:35 (收盘后)

三个节点同时启动 `gsd-worker` 进程，但使用不同的参数。

| 节点 | Shard ID | 触发机制 | 命令 |
| :--- | :--- | :--- | :--- |
| **Server 41** | 0 | `task-orchestrator` | `jobs.sync_tick --scope all --shard-index 0` |
| **Server 58** | 1 | Cron / Docker | `jobs.sync_tick --scope all --shard-index 1` |
| **Server 111** | 2 | Cron / Docker | `jobs.sync_tick --scope all --shard-index 2` |

**执行逻辑 (`sync_tick.py`):**
1.  **启动**: Worker 启动并识别分配给它的 `shard-index`。
2.  **获取任务**: 调用 `TickSyncService.get_sharded_stocks(shard_index)`。
    *   直接从对应的 Redis key (`metadata:stock_codes:shard:{i}`) 获取预计算好的股票列表。
3.  **处理**: 遍历分配的股票，执行分笔数据采集序列（智能矩阵搜索策略）。
    *   Worker 连接本地 `mootdx-api` (Port 8003) 获取数据。
4.  **写入**: 将数据插入本地 ClickHouse 分片。

## 4. 关键配置 (Key Configurations)


### Redis Keys
- `metadata:stock_codes`: 全量股票列表。
- `metadata:stock_codes:shard:{0,1,2}`: 分片后的股票列表。
- `metadata:stock_info`: 股票基础信息（名称、类型）。

### 环境变量
- `REDIS_NODES`: Redis Cluster 节点列表 (逗号分隔，如 `192.168.151.41:16379,192.168.151.58:16379,192.168.151.111:16379`)。
- `MOOTDX_API_URL`: 本地 Mootdx API 地址 (所有节点统一为 `http://localhost:8003`)。
- `CLICKHOUSE_HOST`: 本地 ClickHouse 实例 IP。

## 5. 维护与验证 (Maintenance & Validation)

- **检查分片分布**:
  检查 Redis keys 以验证每个分片的股票数量:
  ```bash
  redis-cli -c -h 192.168.151.41 -p 16379 SCARD metadata:stock_codes:shard:0
  redis-cli -c -h 192.168.151.41 -p 16379 SCARD metadata:stock_codes:shard:1
  redis-cli -c -h 192.168.151.41 -p 16379 SCARD metadata:stock_codes:shard:2
  ```


- **日志**:
  - Server 41: `task-orchestrator` 日志或 `gsd-worker` 日志。
  - Server 58/111: Syslog 或特定的容器执行日志。

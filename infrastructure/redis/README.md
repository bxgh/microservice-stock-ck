# Redis 3-Shard 集群配置文档

## 架构概览

```
  Shard 1          Shard 2          Shard 3
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Node 41     │  │ Node 58     │  │ Node 111    │
│ Master      │  │ Master      │  │ Master      │
│ Slots 0-1/3 │  │ Slots 1/3-2/3 ││ Slots 2/3-1 │
└─────────────┘  └─────────────┘  └─────────────┘
```

**对标 ClickHouse 的高性能分片架构：**
- **并行读写**：3 个主节点同时处理请求
- **负载均衡**：每个节点负责 1/3 的 Hash Slots
- **端口**：**16379** (避免与宿主机或其他服务冲突)

---

## 集群配置

### 节点信息

| 节点 | IP | 角色 | 端口 | 负责槽位 |
|------|----|----|------|----------|
| Server 41 | 192.168.151.41 | Master | 16379 | 0 - 5460 |
| Server 58 | 192.168.151.58 | Master | 16379 | 5461 - 10922 |
| Server 111 | 192.168.151.111 | Master | 16379 | 10923 - 16383 |

**注意**：目前配置为 **3 Master / 0 Replica** (高性能模式)，无数据副本。建议应用程序层做好容错或定期备份。

---

## 运维操作

### 启动/重启集群

```bash
# 一键脚本 (自动处理所有节点)
./infrastructure/redis/deploy_cluster.sh
```

### 检查集群状态

```bash
docker exec microservice-stock-redis redis-cli -p 16379 cluster nodes
```

### 手动连接

```bash
# 连接任意节点
redis-cli -c -h 192.168.151.41 -p 16379
```

---

## 应用程序配置

所有微服务已更新为使用端口 **16379**。

**Python 设置示例 (`settings.py`)**:
```python
REDIS_HOST = "192.168.151.41"
REDIS_PORT = 16379
REDIS_CLUSTER_MODE = True
```

**连接代码示例**:
```python
from redis import RedisCluster

startup_nodes = [
    {"host": "192.168.151.41", "port": "16379"},
    {"host": "192.168.151.58", "port": "16379"},
    {"host": "192.168.151.111", "port": "16379"}
]

rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)
rc.set("foo", "bar")
```

---

## 故障排查

1. **Connection Refused**: 检查端口 16379 是否开放，且 `redis-server` 是否在运行。
2. **MOVED Error**: 确保客户端使用了集群模式 (Cluster Mode)，否则无法自动跳转分片。
3. **Cluster Down**: 如果某个 Master 挂掉且没有 Slave，整个集群可能会进入 FAIL 状态。需尽快重启该节点。

---

## 文件位置

```
infrastructure/redis/
├── deploy_cluster.sh          # 部署脚本
├── node-41/
│   ├── docker-compose.yml
│   └── redis.conf
├── node-58/
│   ├── docker-compose.yml
│   └── redis.conf
└── node-111/
    ├── docker-compose.yml
    └── redis.conf
```

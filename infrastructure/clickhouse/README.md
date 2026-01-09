# ClickHouse 集群部署指南

## 部署架构

ClickHouse 集群采用 3 节点全副本架构 (1 Shard, 3 Replicas)：
- **Server 41** (192.168.151.41) - Leader 节点
- **Server 58** (192.168.151.58) - Follower 节点
- **Server 111** (192.168.151.111) - Follower 节点

## 部署方式

### 方式一：Docker Compose（推荐）

```bash
# 快速部署（自动分发配置 + 启动所有节点）
./infrastructure/clickhouse/scripts/deploy_cluster_compose.sh

# 停止集群
./infrastructure/clickhouse/scripts/stop_cluster_compose.sh

# 单节点操作
cd infrastructure/clickhouse
docker-compose -f docker-compose.node-41.yml up -d
docker-compose -f docker-compose.node-41.yml logs -f
docker-compose -f docker-compose.node-41.yml down
```

### 方式二：Shell 脚本（完全重建）

**警告**: 此方式会删除所有现有数据

```bash
./infrastructure/clickhouse/scripts/full_redeploy_cluster.sh
```

## 配置文件

```
infrastructure/clickhouse/
├── config/
│   ├── config.xml          # 通用配置
│   ├── users.xml           # 用户配置
│   └── config.d/
│       ├── node_41.xml     # Server 41 专用 (server_id=1)
│       ├── node_58.xml     # Server 58 专用 (server_id=2)
│       └── node_111.xml    # Server 111 专用 (server_id=3)
├── docker-compose.node-41.yml
├── docker-compose.node-58.yml
└── docker-compose.node-111.yml
```

## 验证集群状态

```bash
# Keeper 状态
echo mntr | nc -w 2 127.0.0.1 9181

# 集群拓扑
docker exec microservice-stock-clickhouse clickhouse-client --query \
  "SELECT * FROM system.clusters WHERE cluster='stock_cluster'"

# 复制状态
docker exec microservice-stock-clickhouse clickhouse-client --query \
  "SELECT * FROM system.replicas"
```

## 注意事项

1. **网络模式**: 使用 `network_mode: host`，直接使用物理网卡，避免 Docker 网络桥接
2. **配置更新**: 修改配置后需重启集群
3. **数据持久化**: 使用 Docker 命名卷 `microservice-stock_clickhouse_data`
4. **SSH 免密**: 远程节点部署需要 SSH 免密登录 (使用 `bxgh` 用户)

## 常见问题

### Q: 集群无法启动？
A: 检查 Keeper 配置中的 `server_id` 是否匹配（41->1, 58->2, 111->3）

### Q: 数据未同步？
A: 检查 Keeper Quorum 状态，确保 Leader + 2 Followers

### Q: 想切换回 Shell 脚本部署？
A: 先停止 Docker Compose 容器，再执行 `full_redeploy_cluster.sh`

# ClickHouse 集群运维速查表

## 🎯 核心理念

**一个原则**: 所有配置修改都在 Server 41 完成，然后自动同步到其他节点

**三个脚本**: 
- `deploy_cluster_compose.sh` - 完整部署
- `update_config.sh` - 更新配置
- `stop_cluster_compose.sh` - 停止集群

---

## 📋 常用操作

### 启动集群
```bash
./infrastructure/clickhouse/scripts/deploy_cluster_compose.sh
```

### 停止集群
```bash
./infrastructure/clickhouse/scripts/stop_cluster_compose.sh
```

### 更新配置（如添加用户）
```bash
# 1. 编辑配置
vim infrastructure/clickhouse/config/users.xml

# 2. 一键同步并重启
./infrastructure/clickhouse/scripts/update_config.sh users.xml
```

### 查看集群状态
```bash
echo mntr | nc -w 2 127.0.0.1 9181
```

### 查看日志
```bash
docker logs -f microservice-stock-clickhouse
```

---

## 🔑 凭证信息

**管理员**: `admin` / `admin123`  
**默认用户**: `default` / (无密码)

**连接示例**:
```bash
clickhouse-client --user admin --password admin123
```

---

## 🏗️ 架构速览

```
Server 41 (Leader)  ←→  Server 58 (Follower)
       ↕
Server 111 (Follower)

- 3 节点全副本（数据完全相同）
- Keeper 自动选举 Leader
- 使用 Host 网络模式
```

**配置文件位置**:
- Server 41: `~/microservice-stock/infrastructure/clickhouse/config/`
- Server 58/111: `~/microservice-stock-deploy/clickhouse/config/`

---

## 🚨 故障处理

### 集群无法启动
```bash
# 完全重建（会清空数据）
./infrastructure/clickhouse/scripts/full_redeploy_cluster.sh
```

### 单节点无响应
```bash
# 先查看日志
docker logs microservice-stock-clickhouse

# 重启该节点
docker restart microservice-stock-clickhouse
```

### Keeper 无 Leader
```bash
# 检查所有节点的 Keeper 状态
for ip in 41 58 111; do
  echo "=== Server $ip ==="
  echo mntr | ssh bxgh@192.168.151.$ip "nc -w 2 127.0.0.1 9181" | grep zk_server_state
done
```

---

## 💡 重要提醒

1. **配置更新**: 永远只在 Server 41 修改，然后用 `update_config.sh` 同步
2. **数据安全**: `full_redeploy_cluster.sh` 会清空数据，慎用
3. **顺序启动**: Leader 会自动选举，无需担心启动顺序
4. **网络依赖**: 确保三个节点之间的 9181 和 9234 端口互通

---

## 📞 快速诊断命令

```bash
# 一键检查所有节点健康状态
for ip in 41 58 111; do
  echo "=== Server $ip ==="
  ssh bxgh@192.168.151.$ip "docker ps --filter name=clickhouse --format '{{.Status}}'"
done

# 检查用户列表
docker exec microservice-stock-clickhouse clickhouse-client -q "SELECT name FROM system.users"

# 检查集群拓扑
docker exec microservice-stock-clickhouse clickhouse-client -q "SELECT * FROM system.clusters WHERE cluster='stock_cluster'"
```

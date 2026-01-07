# ClickHouse 3节点扩容 - 快速操作指南

## 🎯 目标
将现有 2节点集群（41 + 58）扩展至 3节点（41 + 58 + 111）

---

## 📋 准备好的资源

### 1. 操作文档
- 📖 **[完整扩容方案](file:///home/bxgh/microservice-stock/docs/operations/CLICKHOUSE_3NODE_EXPANSION.md)** - 详细步骤、风险评估、回退方案

### 2. 自动化脚本（已添加可执行权限）
- 🔍 **[pre_expansion_check.sh](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/scripts/pre_expansion_check.sh)** - 前置检查脚本
- 🚀 **[deploy_node111_config.sh](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/scripts/deploy_node111_config.sh)** - 111服务器配置部署
- 🔄 **[update_existing_nodes.sh](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/scripts/update_existing_nodes.sh)** - 41/58配置更新

### 3. 配置文件模板
- **For 111**: [keeper_config_111.xml](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/config/keeper_config_111.xml), [replication_config_111.xml](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/config/replication_config_111.xml)
- **For 41**: [keeper_config_41_3nodes.xml](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/config/keeper_config_41_3nodes.xml), [replication_config_41_3nodes.xml](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/config/replication_config_41_3nodes.xml)
- **For 58**: [keeper_config_58_3nodes.xml](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/config/keeper_config_58_3nodes.xml), [replication_config_58_3nodes.xml](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/config/replication_config_58_3nodes.xml)

---

## ⚡ 快速执行流程（3步法）

### Step 1: 前置检查（所有服务器）

将脚本复制到各服务器并执行检查：

```bash
# 在 41 服务器上
bash pre_expansion_check.sh 41

# 在 58 服务器上
bash pre_expansion_check.sh 58

# 在 111 服务器上
bash pre_expansion_check.sh 111
```

**预期结果**: 所有关键检查通过（✓ PASS）

---

### Step 2: 部署配置（按顺序）

#### 2.1 在 111 服务器上部署配置

```bash
# 确保已将脚本传输到111服务器
sudo bash deploy_node111_config.sh

# 启动 ClickHouse
sudo systemctl start clickhouse-server

# 验证启动成功
systemctl status clickhouse-server
echo "mntr" | nc localhost 9181
```

#### 2.2 更新 58 服务器（Follower 优先）

```bash
# 首先确认 58 是 Follower
echo "mntr" | nc localhost 9181 | grep zk_server_state

# 更新配置
sudo bash update_existing_nodes.sh 58

# 重启服务
sudo systemctl restart clickhouse-server

# 验证重启成功  
systemctl status clickhouse-server
echo "mntr" | nc localhost 9181 | grep zk_server_state
```

#### 2.3 更新 41 服务器（Leader 最后）

```bash
# 确认 41 是 Leader
echo "mntr" | nc localhost 9181 | grep zk_server_state

# 更新配置
sudo bash update_existing_nodes.sh 41

# 重启服务
sudo systemctl restart clickhouse-server

# 验证重启成功
systemctl status clickhouse-server
echo "mntr" | nc localhost 9181 | grep zk_server_state
```

---

### Step 3: 验证 3节点集群

在任意节点上执行：

```sql
-- 验证 Keeper 集群状态（应显示3个节点）
SELECT * FROM system.zookeeper WHERE path = '/keeper';

-- 创建测试表
CREATE TABLE test_3nodes ON CLUSTER stock_cluster
(
    id UInt32,
    message String,
    created_at DateTime DEFAULT now()
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/test_3nodes', '{replica}')
ORDER BY id;

-- 在 41 上插入数据
INSERT INTO test_3nodes (id, message) VALUES (1, 'From 41');

-- 在 58/111 上查询（应该能看到数据）
SELECT * FROM test_3nodes;

-- 检查副本状态（应显示 total_replicas=3, active_replicas=3）
SELECT 
    database, table,
    total_replicas,
    active_replicas,
    is_readonly
FROM system.replicas
WHERE table = 'test_3nodes'
FORMAT Vertical;

-- 清理测试表
DROP TABLE test_3nodes ON CLUSTER stock_cluster;
```

---

## 🔍 关键验证点

### ✅ 扩容成功的标志

1. **Keeper 集群**: 3个节点都显示在 `system.zookeeper`
2. **副本数量**: `total_replicas = 3`, `active_replicas = 3`
3. **无只读表**: `is_readonly = 0`
4. **同步队列**: `queue_size` 逐渐降为 0
5. **跨节点写入**: 在任意节点写入，其他节点能立即读取

### 🚨 故障排查

**问题**: 111节点无法加入 Keeper 集群

```bash
# 检查网络连通性
nc -zv 192.168.151.41 9234
nc -zv 192.168.151.58 9234

# 检查配置文件
cat /etc/clickhouse-server/config.d/keeper_config.xml | grep server_id
cat /etc/clickhouse-server/config.d/keeper_config.xml | grep hostname

# 查看日志
tail -f /var/log/clickhouse-server/clickhouse-server.log | grep -i keeper
```

**问题**: 副本状态为只读

```sql
-- 检查 Keeper 会话
SELECT * FROM system.replicas WHERE is_readonly = 1 FORMAT Vertical;

-- 重启只读副本的 ClickHouse
systemctl restart clickhouse-server
```

---

## ⏰ 推荐执行时间

- 🟢 **最佳**: 周末（非交易日）
- 🟡 **次佳**: 交易日盘后（15:30 - 23:00）
- 🔴 **避免**: 交易时段（09:30 - 15:00）

**当前时间**: 2026-01-07 14:43（周二盘中）  
**建议**: 等到今晚 **15:30** 之后或本周末执行

---

## 📦 文件传输命令

将脚本从本地传输到远程服务器：

```bash
# 从开发机传输到 111 服务器
scp infrastructure/clickhouse/scripts/pre_expansion_check.sh root@192.168.151.111:/tmp/
scp infrastructure/clickhouse/scripts/deploy_node111_config.sh root@192.168.151.111:/tmp/

# 传输到 41 服务器
scp infrastructure/clickhouse/scripts/update_existing_nodes.sh root@192.168.151.41:/tmp/

# 传输到 58 服务器
scp infrastructure/clickhouse/scripts/update_existing_nodes.sh root@192.168.151.58:/tmp/
```

---

## 🔄 回退方案

如果扩容失败：

```bash
# 1. 停止 111 节点
ssh root@192.168.151.111 "systemctl stop clickhouse-server"

# 2. 在 41/58 上恢复备份配置
cd /backup/clickhouse-config-<时间戳>
cp config.d/keeper_config.xml /etc/clickhouse-server/config.d/
cp config.d/replication_config.xml /etc/clickhouse-server/config.d/

# 3. 重启 41/58 (先Follower后Leader)
systemctl restart clickhouse-server

# 4. 验证 2节点集群恢复
clickhouse-client --query "SELECT * FROM system.replicas FORMAT Vertical"
```

---

## 📞 支持

如遇问题，检查以下日志：

```bash
# ClickHouse 主日志
tail -f /var/log/clickhouse-server/clickhouse-server.log

# Keeper 日志
tail -f /var/log/clickhouse-server/clickhouse-server.log | grep -i keeper

# 系统服务状态
journalctl -u clickhouse-server -f
```

---

**创建时间**: 2026-01-07 14:43  
**状态**: ✅ 就绪，随时可执行

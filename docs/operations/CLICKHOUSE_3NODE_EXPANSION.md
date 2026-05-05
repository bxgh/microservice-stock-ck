# ClickHouse 集群 3 节点扩容方案

## 📋 扩容概述

**目标**: 将现有的 2 节点 ClickHouse 集群（41 + 58）扩容至 3 节点（41 + 58 + 111），实现真正的高可用和防脑裂。

**新节点信息**:
- **IP地址**: 192.168.151.111
- **Keeper ID**: 3
- **Replica名称**: server111
- **角色**: Keeper Follower + Data Replica

**扩容收益**:
- ✅ **防脑裂**: Raft 多数派从 1/2 提升至 2/3，网络分区时不会产生双 Leader
- ✅ **自动故障切换**: 任意节点故障，剩余 2 节点仍可选举新 Leader，集群保持可写
- ✅ **负载均衡**: 3 个数据副本，可分散读写压力
- ✅ **数据安全**: 数据冗余度从 2 提升至 3

---

## ⚠️ 风险评估

| 风险项 | 影响 | 缓解措施 |
|:-------|:-----|:---------|
| **配置错误导致集群不可用** | 高 | 在非业务高峰期操作；准备回退方案 |
| **Keeper 仲裁失败** | 高 | 逐节点添加，每步验证 `system.zookeeper` 状态 |
| **数据同步耗时过长** | 中 | 新节点仅同步元数据，无需全量数据迁移 |
| **网络配置错误** | 中 | 预先验证 9000/9009/9181/9234 端口互通 |

**建议操作时间**: 非交易日（周末）或交易日盘后（15:30 之后）

---

## 📝 前置检查清单

### 1. 网络连通性测试

在 **41/58/111** 三台服务器上分别执行：

```bash
# 测试 ClickHouse 原生协议端口 (9000)
nc -zv 192.168.151.41 9000
nc -zv 192.168.151.58 9000
nc -zv 192.168.151.111 9000

# 测试副本同步端口 (9009)
nc -zv 192.168.151.41 9009
nc -zv 192.168.151.58 9009
nc -zv 192.168.151.111 9009

# 测试 Keeper 客户端端口 (9181)
nc -zv 192.168.151.41 9181
nc -zv 192.168.151.58 9181
nc -zv 192.168.151.111 9181

# 测试 Keeper Raft 端口 (9234)
nc -zv 192.168.151.41 9234
nc -zv 192.168.151.58 9234
nc -zv 192.168.151.111 9234
```

**预期**: 所有端口都应返回 `succeeded`

---

### 2. 确认当前集群状态

在 **41 或 58** 服务器上执行：

```bash
# 查询 Keeper 状态
echo "mntr" | nc 192.168.151.41 9181

# 查询复制状态
clickhouse-client --query "
SELECT 
    database, table, 
    is_leader, is_readonly, 
    total_replicas, active_replicas
FROM system.replicas
FORMAT Vertical
"
```

**预期**:
- Keeper 状态为 `follower` 或 `leader`
- 所有表的 `is_readonly = 0`
- `total_replicas = 2`, `active_replicas = 2`

---

### 3. 数据备份（关键！）

在 **41** 服务器上执行：

```bash
# 备份 ClickHouse 配置
sudo tar -czf /backup/clickhouse-config-$(date +%Y%m%d).tar.gz \
    /etc/clickhouse-server/config.d/

# 备份 Keeper 元数据快照
sudo tar -czf /backup/keeper-data-$(date +%Y%m%d).tar.gz \
    /var/lib/clickhouse/coordination/

# 备份关键业务数据（可选，但强烈推荐）
clickhouse-client --query "
CREATE TABLE IF NOT EXISTS backup.daily_kline AS daily_kline
ENGINE = MergeTree() ORDER BY (stock_code, trade_date)
AS SELECT * FROM daily_kline WHERE trade_date >= '2026-01-01'
"
```

---

## 🚀 扩容步骤

### 步骤 1: 准备新节点配置文件（111 服务器）

#### 1.1 创建 Keeper 配置

在 **111** 服务器上创建 `/etc/clickhouse-server/config.d/keeper_config.xml`:

```xml
<?xml version="1.0"?>
<clickhouse>
    <keeper_server>
        <tcp_port>9181</tcp_port>
        <server_id>3</server_id>
        <log_storage_path>/var/lib/clickhouse/coordination/log</log_storage_path>
        <snapshot_storage_path>/var/lib/clickhouse/coordination/snapshots</snapshot_storage_path>

        <coordination_settings>
            <operation_timeout_ms>10000</operation_timeout_ms>
            <session_timeout_ms>30000</session_timeout_ms>
            <raft_logs_level>warning</raft_logs_level>
        </coordination_settings>

        <raft_configuration>
            <server>
                <id>1</id>
                <hostname>192.168.151.41</hostname>
                <port>9234</port>
            </server>
            <server>
                <id>2</id>
                <hostname>192.168.151.58</hostname>
                <port>9234</port>
            </server>
            <server>
                <id>3</id>
                <hostname>192.168.151.111</hostname>
                <port>9234</port>
            </server>
        </raft_configuration>
    </keeper_server>
</clickhouse>
```

#### 1.2 创建复制配置

在 **111** 服务器上创建 `/etc/clickhouse-server/config.d/replication_config.xml`:

```xml
<?xml version="1.0"?>
<clickhouse>
    <!-- 宏定义 - 用于复制表路径 -->
    <macros>
        <shard>01</shard>
        <replica>server111</replica>
    </macros>

    <!-- 连接到 ClickHouse Keeper 集群 -->
    <zookeeper>
        <node>
            <host>192.168.151.41</host>
            <port>9181</port>
        </node>
        <node>
            <host>192.168.151.58</host>
            <port>9181</port>
        </node>
        <node>
            <host>192.168.151.111</host>
            <port>9181</port>
        </node>
        <session_timeout_ms>30000</session_timeout_ms>
    </zookeeper>

    <!-- 集群配置 -->
    <remote_servers>
        <stock_cluster>
            <shard>
                <internal_replication>true</internal_replication>
                <replica>
                    <host>192.168.151.41</host>
                    <port>9000</port>
                </replica>
                <replica>
                    <host>192.168.151.58</host>
                    <port>9000</port>
                </replica>
                <replica>
                    <host>192.168.151.111</host>
                    <port>9000</port>
                </replica>
            </shard>
        </stock_cluster>
    </remote_servers>

    <!-- 允许远程连接 -->
    <listen_host>0.0.0.0</listen_host>
    
    <!-- 关键：告诉其他副本如何连接我 -->
    <interserver_http_host>192.168.151.111</interserver_http_host>
</clickhouse>
```

#### 1.3 启动新节点（仅启动，暂不加入集群）

```bash
# 在 111 服务器上
sudo systemctl start clickhouse-server
sudo systemctl status clickhouse-server

# 验证 ClickHouse 启动成功
clickhouse-client --query "SELECT version()"
```

---

### 步骤 2: 更新现有节点配置（41 和 58）

#### 2.1 更新 Keeper 配置

在 **41** 服务器上修改 `/etc/clickhouse-server/config.d/keeper_config.xml`，在 `<raft_configuration>` 中添加第三个节点：

```xml
<server>
    <id>3</id>
    <hostname>192.168.151.111</hostname>
    <port>9234</port>
</server>
```

**完整配置示例**（41 服务器）：

```xml
<?xml version="1.0"?>
<clickhouse>
    <keeper_server>
        <tcp_port>9181</tcp_port>
        <server_id>1</server_id>
        <log_storage_path>/var/lib/clickhouse/coordination/log</log_storage_path>
        <snapshot_storage_path>/var/lib/clickhouse/coordination/snapshots</snapshot_storage_path>

        <coordination_settings>
            <operation_timeout_ms>10000</operation_timeout_ms>
            <session_timeout_ms>30000</session_timeout_ms>
            <raft_logs_level>warning</raft_logs_level>
        </coordination_settings>

        <raft_configuration>
            <server>
                <id>1</id>
                <hostname>192.168.151.41</hostname>
                <port>9234</port>
            </server>
            <server>
                <id>2</id>
                <hostname>192.168.151.58</hostname>
                <port>9234</port>
            </server>
            <server>
                <id>3</id>
                <hostname>192.168.151.111</hostname>
                <port>9234</port>
            </server>
        </raft_configuration>
    </keeper_server>
</clickhouse>
```

**在 58 服务器上执行相同操作**。

#### 2.2 更新复制配置

在 **41** 和 **58** 服务器上修改 `/etc/clickhouse-server/config.d/replication_config.xml`：

1. 在 `<zookeeper>` 部分添加第三个节点：

```xml
<node>
    <host>192.168.151.111</host>
    <port>9181</port>
</node>
```

2. 在 `<remote_servers>` 的 `<stock_cluster>` 中添加第三个副本：

```xml
<replica>
    <host>192.168.151.111</host>
    <port>9000</port>
</replica>
```

---

### 步骤 3: 滚动重启（关键步骤！）

> ⚠️ **重要**: 必须先重启非 Leader 节点，最后重启 Leader 节点

#### 3.1 确认当前 Leader

```bash
# 在 41 或 58 上执行
echo "mntr" | nc 192.168.151.41 9181 | grep zk_server_state
echo "mntr" | nc 192.168.151.58 9181 | grep zk_server_state
```

假设 **41 是 Leader**，**58 是 Follower**。

#### 3.2 重启 Follower 节点（58）

```bash
# 在 58 服务器上
sudo systemctl restart clickhouse-server
sleep 10

# 验证重启成功
echo "mntr" | nc 192.168.151.58 9181 | grep zk_server_state
clickhouse-client --query "SELECT 1"
```

#### 3.3 重启 Leader 节点（41）

```bash
# 在 41 服务器上
sudo systemctl restart clickhouse-server
sleep 10

# 验证重启成功
echo "mntr" | nc 192.168.151.41 9181 | grep zk_server_state
```

#### 3.4 重启新节点（111）

```bash
# 在 111 服务器上
sudo systemctl restart clickhouse-server
sleep 10

# 验证 Keeper 加入集群
echo "mntr" | nc 192.168.151.111 9181 | grep zk_server_state
```

---

### 步骤 4: 验证 Keeper 集群状态

在 **任意节点** 上执行：

```bash
# 查看 Keeper 集群成员
clickhouse-client --query "
SELECT * FROM system.zookeeper WHERE path = '/keeper'
"

# 验证 3 节点都已注册
echo "conf" | nc 192.168.151.41 9181
echo "conf" | nc 192.168.151.58 9181
echo "conf" | nc 192.168.151.111 9181
```

**预期输出**: 应显示 3 个 server (id=1,2,3)

---

### 步骤 5: 创建测试表验证数据同步

在 **41** 服务器上执行：

```sql
-- 创建测试数据库
CREATE DATABASE IF NOT EXISTS test_replication ON CLUSTER stock_cluster;

-- 创建复制表
CREATE TABLE test_replication.sync_test ON CLUSTER stock_cluster
(
    id UInt32,
    message String,
    created_at DateTime DEFAULT now()
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/sync_test', '{replica}')
ORDER BY id;

-- 在 41 上插入数据
INSERT INTO test_replication.sync_test (id, message) 
VALUES (1, 'From Server 41');

-- 等待 3 秒后查询
SELECT sleep(3);
SELECT * FROM test_replication.sync_test;
```

在 **58** 和 **111** 服务器上分别执行：

```sql
-- 应该能看到 41 插入的数据
SELECT * FROM test_replication.sync_test;

-- 在 58 上插入数据
INSERT INTO test_replication.sync_test (id, message) 
VALUES (2, 'From Server 58');

-- 在 111 上插入数据
INSERT INTO test_replication.sync_test (id, message) 
VALUES (3, 'From Server 111');
```

在 **任意节点** 上验证：

```sql
-- 应该看到 3 条记录
SELECT * FROM test_replication.sync_test ORDER BY id;

-- 验证副本状态
SELECT 
    database, table,
    total_replicas,
    active_replicas,
    is_readonly
FROM system.replicas
WHERE table = 'sync_test'
FORMAT Vertical;
```

**预期**:
- `total_replicas = 3`
- `active_replicas = 3`
- `is_readonly = 0`

---

### 步骤 6: 验证现有业务表

```sql
-- 检查所有复制表状态
SELECT 
    database, table,
    is_leader,
    total_replicas,
    active_replicas,
    queue_size,
    inserts_in_queue,
    merges_in_queue,
    is_readonly,
    last_queue_update
FROM system.replicas
ORDER BY database, table
FORMAT Vertical;
```

**预期**:
- 所有表 `total_replicas = 3`
- `active_replicas = 3`
- `queue_size` 应逐渐降至 0（表示同步完成）
- `is_readonly = 0`

---

### 步骤 7: 清理测试数据

```sql
-- 删除测试表
DROP TABLE test_replication.sync_test ON CLUSTER stock_cluster;
DROP DATABASE test_replication ON CLUSTER stock_cluster;
```

---

## 🔄 回退方案

如果扩容失败，需要回退到 2 节点配置：

### 回退步骤

1. **停止 111 节点**:
   ```bash
   # 在 111 服务器上
   sudo systemctl stop clickhouse-server
   ```

2. **还原 41 和 58 的配置**:
   ```bash
   # 在 41 和 58 上分别执行
   sudo cp /backup/clickhouse-config-<日期>.tar.gz /tmp/
   cd /tmp && tar -xzf clickhouse-config-<日期>.tar.gz
   sudo cp -r etc/clickhouse-server/config.d/* /etc/clickhouse-server/config.d/
   ```

3. **重启 41 和 58**:
   ```bash
   # 先重启 58（Follower）
   sudo systemctl restart clickhouse-server
   
   # 再重启 41（Leader）
   sudo systemctl restart clickhouse-server
   ```

4. **验证 2 节点集群恢复**:
   ```bash
   clickhouse-client --query "
   SELECT * FROM system.replicas FORMAT Vertical
   "
   ```

---

## 📊 后续维护建议

### 1. 持续监控指标

```sql
-- 每日检查复制状态
SELECT 
    database, table,
    total_replicas,
    active_replicas,
    queue_size,
    is_readonly,
    last_queue_update
FROM system.replicas
WHERE active_replicas < total_replicas OR is_readonly = 1
FORMAT Vertical;
```

### 2. Keeper 健康检查

```bash
# 添加到 cron 任务（每小时执行）
*/60 * * * * echo "ruok" | nc 192.168.151.41 9181 >> /var/log/keeper_health.log
```

### 3. 告警规则（Prometheus + Grafana）

```yaml
# 副本数量不足告警
- alert: ClickHouseReplicaDown
  expr: clickhouse_replicas_active < clickhouse_replicas_total
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "ClickHouse replica down on {{ $labels.instance }}"

# Keeper 连接异常
- alert: KeeperSessionExpired
  expr: clickhouse_replica_is_session_expired == 1
  for: 1m
  labels:
    severity: critical
```

---

## ✅ 预期成果

扩容完成后，系统将具备以下能力：

1. ✅ **真正的高可用**: 任意 1 台服务器故障，集群仍可正常工作
2. ✅ **自动故障切换**: Keeper 自动选举新 Leader，无需人工介入
3. ✅ **防脑裂**: 网络分区时，多数派节点（2/3）继续提供服务
4. ✅ **数据三副本**: 数据安全性进一步提升
5. ✅ **负载均衡**: 可通过 NGINX 或客户端负载均衡分散读写压力

---

## 📚 参考资料

- [ClickHouse Keeper 官方文档](https://clickhouse.com/docs/en/guides/sre/keeper/clickhouse-keeper)
- [复制表引擎文档](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/replication)
- [当前集群架构文档](file:///home/bxgh/microservice-stock/docs/architecture/clickhouse-replicated-cluster.md)

---

**创建时间**: 2026-01-07  
**作者**: AI Assistant  
**状态**: 待执行

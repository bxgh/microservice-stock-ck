# Server 111 故障排查和修复指南

## 当前状态
- ✅ Server 41: 已成功更新为3节点配置，Keeper运行正常（leader）
- ✅ Server 58: 已成功更新为3节点配置，Keeper运行正常（follower）
- ❌ Server 111: 容器运行但Keeper未响应，未加入集群

## 问题诊断

### 步骤1: SSH到111服务器
```bash
ssh bxgh@192.168.151.111
```

### 步骤2: 检查容器状态
```bash
docker ps | grep clickhouse
# 应该显示容器正在运行
```

### 步骤3: 检查配置文件是否存在
```bash
ls -la /home/bxgh/microservice-stock/infrastructure/clickhouse/config/
# 应该看到 keeper_config.xml 和 replication_config.xml
```

### 步骤4: 检查配置文件内容
```bash
# 检查keeper配置
sudo cat /home/bxgh/microservice-stock/infrastructure/clickhouse/config/keeper_config.xml | grep server_id
# 应该显示: <server_id>3</server_id>

# 检查replica配置
sudo cat /home/bxgh/microservice-stock/infrastructure/clickhouse/config/replication_config.xml | grep replica
# 应该显示: <replica>server111</replica>
```

### 步骤5: 检查容器日志
```bash
docker logs --tail 100 microservice-stock-clickhouse 2>&1 | grep -i keeper
# 查找任何错误信息
```

## 修复方案

### 方案A: 重新创建配置文件

如果配置文件不正确或不存在，手动创建：

```bash
# 1. 创建keeper配置
sudo tee /home/bxgh/microservice-stock/infrastructure/clickhouse/config/keeper_config.xml > /dev/null <<'EOF'
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
EOF

# 2. 创建replication配置
sudo tee /home/bxgh/microservice-stock/infrastructure/clickhouse/config/replication_config.xml > /dev/null <<'EOF'
<?xml version="1.0"?>
<clickhouse>
    <macros>
        <shard>01</shard>
        <replica>server111</replica>
    </macros>

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

    <listen_host>0.0.0.0</listen_host>
    <interserver_http_host>192.168.151.111</interserver_http_host>
</clickhouse>
EOF

# 3. 重启容器
docker restart microservice-stock-clickhouse

# 4. 等待30秒
sleep 30

# 5. 验证
echo "mntr" | nc localhost 9181 | grep zk_server_state
# 应该显示: zk_server_state follower 或 leader
```

### 方案B: 检查docker-compose配置

如果容器没有正确挂载配置文件：

```bash
# 1. 检查docker-compose文件
cat /home/bxgh/microservice-stock/docker-compose.infrastructure.yml | grep -A 20 clickhouse

# 2. 确认volumes挂载
docker inspect microservice-stock-clickhouse | grep -A 10 Mounts

# 3. 如果挂载不正确，重新创建容器
cd /home/bxgh/microservice-stock
docker-compose -f docker-compose.infrastructure.yml down clickhouse
docker-compose -f docker-compose.infrastructure.yml up -d clickhouse
```

### 方案C: 清理Keeper数据重新加入

如果Keeper有旧数据冲突：

```bash
# 1. 停止容器
docker stop microservice-stock-clickhouse

# 2. 清理Keeper数据（谨慎！）
docker exec microservice-stock-clickhouse rm -rf /var/lib/clickhouse/coordination/* 2>/dev/null || true

# 3. 启动容器
docker start microservice-stock-clickhouse

# 4. 等待并验证
sleep 30
echo "mntr" | nc localhost 9181 | grep zk_server_state
```

## 验证成功

在111服务器上执行：

```bash
# 1. Keeper状态
echo "mntr" | nc localhost 9181 | grep zk_server_state
# 应该显示: zk_server_state follower

# 2. ClickHouse连接
docker exec microservice-stock-clickhouse clickhouse-client --query "SELECT 1"
# 应该返回: 1

# 3. 副本状态
docker exec microservice-stock-clickhouse clickhouse-client --query "
SELECT max(total_replicas), max(active_replicas) 
FROM system.replicas
"
# 应该显示: 3  3
```

## 回到41服务器验证

```bash
# 退出111
exit

# 在41上检查集群状态
bash /home/bxgh/microservice-stock/infrastructure/clickhouse/scripts/check_cluster_status.sh
```

## 预期最终结果

```
[1] Keeper集群状态
-------------------
Server 41 (192.168.151.41): leader 或 follower
Server 58 (192.168.151.58): follower 或 leader  
Server 111 (192.168.151.111): follower

[2] 副本状态
-------------------
总副本数   : 3
在线副本数: 3
只读表数   : 0
同步队列   : 0 或 很小的数字
```

## 如果还是失败

请收集以下信息：

```bash
# 在111上执行
docker logs --tail 200 microservice-stock-clickhouse > /tmp/clickhouse_111.log 2>&1
cat /tmp/clickhouse_111.log | grep -i -E "(error|exception|keeper|fatal)"
```

将错误信息发给我，我会进一步分析。

---

**创建时间**: 2026-01-07 15:33
**状态**: 等待手动执行

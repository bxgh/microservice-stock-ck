# Server 111 ClickHouse 问题诊断报告

**报告时间**: 2026-01-08 17:00  
**服务器**: 192.168.151.111  
**问题类型**: ClickHouse Keeper 集群同步失败  
**影响范围**: 无法进行分布式分笔数据采集

---

## 1. 问题现象

### 1.1 主要症状

在 Server 111 上运行 `gsd-worker` 容器时，无法连接到本地 ClickHouse：

```bash
ConnectionResetError: [Errno 104] Connection reset by peer
```

### 1.2 错误堆栈

```python
File "/usr/local/lib/python3.12/site-packages/asynch/proto/connection.py", line 550, in _init_connection
    await self.receive_hello()
File "/usr/local/lib/python3.12/site-packages/asynch/proto/connection.py", line 239, in receive_hello
    packet_type = await self.reader.read_varint()
...
ConnectionResetError: [Errno 104] Connection reset by peer
```

---

## 2. 根本原因

### 2.1 ClickHouse 错误日志

从 `/var/log/clickhouse-server/clickhouse-server.err.log` 发现：

```
Table is in readonly mode (replica path: /clickhouse/tables/01/stock_kline_daily/replicas/server111), 
cannot update queue. (TABLE_IS_READ_ONLY)
```

```
Session expired. (KEEPER_EXCEPTION)
```

### 2.2 问题分析

1. **ClickHouse Keeper 会话过期**
   - Keeper 集群节点之间失去同步
   - Server 111 的 Keeper 无法与其他节点通信

2. **表进入只读模式**
   - 由于 Keeper 会话丢失，ReplicatedMergeTree 表自动进入只读保护模式
   - 无法写入新数据

3. **连接被拒绝**
   - ClickHouse 检测到表状态异常，主动断开新的客户端连接

---

## 3. 验证步骤

### 3.1 基础服务检查

```bash
# ClickHouse 服务状态
ssh bxgh@192.168.151.111 "docker ps | grep clickhouse"
# 输出: 容器正常运行 (Up 22 hours)

# ClickHouse 版本
ssh bxgh@192.168.151.111 "docker exec microservice-stock-clickhouse clickhouse-client -q 'SELECT version()'"
# 输出: 25.10.1.3832

# 端口监听
ssh bxgh@192.168.151.111 "netstat -tunlp | grep 9000"
# 输出: tcp 0.0.0.0:9000 LISTEN (正常)
```

### 3.2 网络连通性检查

```bash
# Ping 测试
ssh bxgh@192.168.151.111 "ping -c 2 192.168.151.111"
# 输出: 0% packet loss (正常)

# Telnet 测试
ssh bxgh@192.168.151.111 "telnet 192.168.151.111 9000"
# 输出: Connected (正常)
```

### 3.3 ClickHouse 内部查询

```bash
# 用户权限
ssh bxgh@192.168.151.111 "docker exec microservice-stock-clickhouse clickhouse-client -q 'SELECT name, host_ip FROM system.users'"
# 输出: default, stock_user, admin (正常)
```

**结论**: 基础服务、网络、权限均正常，问题在于 **Keeper 集群同步**。

---

## 4. 解决方案

### 方案 A: 重启 ClickHouse 服务 (推荐)

```bash
# 1. 停止 ClickHouse
ssh bxgh@192.168.151.111 "docker stop microservice-stock-clickhouse"

# 2. 等待 10 秒
sleep 10

# 3. 启动 ClickHouse
ssh bxgh@192.168.151.111 "docker start microservice-stock-clickhouse"

# 4. 等待服务就绪 (约 30 秒)
sleep 30

# 5. 验证 Keeper 状态
ssh bxgh@192.168.151.111 "docker exec microservice-stock-clickhouse clickhouse-client -q 'SELECT * FROM system.zookeeper WHERE path = \"/\"'"
```

### 方案 B: 检查 Keeper 配置

```bash
# 1. 查看 Keeper 配置
ssh bxgh@192.168.151.111 "docker exec microservice-stock-clickhouse cat /etc/clickhouse-server/config.d/keeper_config.xml"

# 2. 检查关键配置项:
#    - server_id: 应为 3
#    - raft_configuration: 应包含 server1(41), server2(58), server3(111)
#    - tcp_port: 9181

# 3. 如果配置有误，修复后重启
```

### 方案 C: 重建 Keeper 集群 (最后手段)

**警告**: 此方案会清空 Keeper 数据，仅在其他方案无效时使用。

```bash
# 1. 停止所有节点的 ClickHouse
for server in 41 58 111; do
    ssh bxgh@192.168.151.$server "docker stop microservice-stock-clickhouse"
done

# 2. 清理 Keeper 数据 (仅 Server 111)
ssh bxgh@192.168.151.111 "docker exec microservice-stock-clickhouse rm -rf /var/lib/clickhouse/coordination/*"

# 3. 按顺序启动 (41 -> 58 -> 111)
for server in 41 58 111; do
    ssh bxgh@192.168.151.$server "docker start microservice-stock-clickhouse"
    sleep 30
done
```

---

## 5. 验证修复

修复后，执行以下命令验证：

```bash
# 1. 测试 ClickHouse 连接
ssh bxgh@192.168.151.111 "docker run --rm --network host \
  -e CLICKHOUSE_HOST=192.168.151.111 \
  -e CLICKHOUSE_PORT=9000 \
  -e MOOTDX_API_URL=http://localhost:8003 \
  gsd-worker:latest \
  jobs.sync_tick --scope config --date 20260107 2>&1 | head -20"

# 预期输出: 
# - "✓ ClickHouse 连接池初始化完成"
# - 无 ConnectionResetError

# 2. 检查表状态
ssh bxgh@192.168.151.111 "docker exec microservice-stock-clickhouse clickhouse-client -q \
  'SELECT database, table, is_readonly FROM system.replicas WHERE database = \"stock_data\"'"

# 预期输出: is_readonly = 0 (所有表)
```

---

## 6. 预防措施

### 6.1 监控 Keeper 健康状态

添加定时检查脚本：

```bash
#!/bin/bash
# /home/bxgh/scripts/check_keeper_health.sh

for server in 41 58 111; do
    echo "Checking Server $server..."
    ssh bxgh@192.168.151.$server "docker exec microservice-stock-clickhouse clickhouse-client -q \
      'SELECT count() FROM system.zookeeper WHERE path = \"/\"' 2>&1"
done
```

### 6.2 配置告警

在 `task-orchestrator` 中添加 ClickHouse 健康检查任务，监控：
- Keeper 连接状态
- 表的 `is_readonly` 状态
- Keeper 会话超时

---

## 7. 相关文档

- ClickHouse Keeper 官方文档: https://clickhouse.com/docs/en/guides/sre/keeper/clickhouse-keeper
- 集群架构文档: `docs/architecture/clickhouse-replicated-cluster.md`
- 分布式采集文档: `docs/operations/DISTRIBUTED_CLUSTER_STATUS_20260108.md`

---

## 8. 联系信息

**问题报告人**: AI Assistant  
**服务器管理员**: Server 111 运维团队  
**优先级**: P1 (影响分布式采集功能)

---

*文档生成时间: 2026-01-08 17:00*  
*下次更新: 问题解决后*

# 运维操作手册 (Runbook)

> **更新时间**: 2026-01-08  
> **适用范围**: 三节点集群 (41/58/111)

---

## 1. 日常操作

### 1.1 服务状态检查

```bash
# 在任意节点执行
ssh bxgh@192.168.151.41 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
ssh bxgh@192.168.151.58 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
ssh bxgh@192.168.151.111 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### 1.2 ClickHouse 集群状态

```bash
# Keeper 状态
for ip in 41 58 111; do
  echo "=== Server $ip ==="
  echo "mntr" | nc 192.168.151.$ip 9181 | grep -E "zk_server_state|zk_synced_followers"
done

# 副本状态
clickhouse-client --query "
SELECT 
    database, table, 
    total_replicas, active_replicas,
    is_readonly
FROM system.replicas 
WHERE active_replicas < total_replicas
"
```

### 1.3 代码更新部署

```bash
# 在 Server 41 执行
cd /home/bxgh/microservice-stock
git push gitlab feature/quant-strategy

# 在各节点拉取并重建
for ip in 58 111; do
  ssh bxgh@192.168.151.$ip "cd /home/bxgh/microservice-stock && \
    git pull gitlab feature/quant-strategy && \
    docker-compose build gsd-worker"
done
```

---

## 2. 分布式采集操作

### 2.1 手动触发全市场采集

```bash
# 在 Server 41 执行
/home/bxgh/microservice-stock/scripts/distributed_tick_sync.sh $(date +%Y%m%d) all
```

### 2.2 单节点采集测试

```bash
# Server 41 (SHARD=0)
docker-compose run --rm gsd-worker python -m jobs.sync_tick --scope all

# Server 58 (SHARD=1)
ssh bxgh@192.168.151.58 "cd /home/bxgh/microservice-stock && \
  docker-compose run --rm gsd-worker python -m jobs.sync_tick --scope all"
```

---

## 3. 故障恢复

### 3.1 单节点故障

**症状**: 某节点服务不可达

**诊断**:
```bash
ping 192.168.151.X
ssh bxgh@192.168.151.X "systemctl status docker"
```

**恢复**:
```bash
# 重启 Docker 服务
ssh bxgh@192.168.151.X "sudo systemctl restart docker"

# 重启所有容器
ssh bxgh@192.168.151.X "cd /home/bxgh/microservice-stock && docker-compose up -d"
```

**影响**: 集群自动降级，剩余 2 节点继续工作

---

### 3.2 Keeper 选举失败

**症状**: 所有节点报 `is_session_expired`

**诊断**:
```bash
for ip in 41 58 111; do
  echo "=== Server $ip ==="
  echo "ruok" | nc 192.168.151.$ip 9181
done
```

**恢复**:
```bash
# 按顺序重启 ClickHouse (先 Follower 后 Leader)
# 1. 确认 Leader 节点
echo "mntr" | nc 192.168.151.41 9181 | grep zk_server_state
echo "mntr" | nc 192.168.151.58 9181 | grep zk_server_state

# 2. 先重启 Follower
ssh bxgh@192.168.151.111 "sudo systemctl restart clickhouse-server"
sleep 30

# 3. 最后重启 Leader
ssh bxgh@192.168.151.58 "sudo systemctl restart clickhouse-server"
```

---

### 3.3 mootdx-api 返回空数据

**症状**: 采集日志显示 `返回 0 只股票`

**恢复**:
```bash
# 重新选择最优服务器
docker exec microservice-stock-mootdx-api python -m mootdx bestip

# 重启容器
docker restart microservice-stock-mootdx-api
```

---

## 4. 监控告警

### 4.1 关键指标

| 指标 | 正常值 | 告警阈值 |
|------|--------|----------|
| `active_replicas` | 3 | < 3 |
| Keeper `zk_synced_followers` | 2 | < 2 |
| 采集时间 | < 30分钟 | > 60分钟 |

### 4.2 日志位置

| 服务 | 日志路径 |
|------|----------|
| ClickHouse | `/var/log/clickhouse-server/` |
| Docker 容器 | `docker logs <container>` |
| gsd-worker | `./logs/gsd-worker/` |

---

## 5. 定期维护

| 任务 | 周期 | 命令 |
|------|------|------|
| 日志清理 | 每周日 | 自动 (tasks.yml) |
| ClickHouse 系统表清理 | 每周日 | 自动 (tasks.yml) |
| 数据审计 | 每周日 | 自动 (weekly_deep_audit) |

---

## 6. 联系方式

| 问题类型 | 处理方式 |
|----------|----------|
| 采集失败 | 检查 mootdx-api + 网络 |
| 集群故障 | 按 3.1/3.2 流程恢复 |
| 数据不一致 | 等待 weekly_deep_audit 自愈 |

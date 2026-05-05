# 集群容器配置说明

> **更新时间**: 2026-01-08  
> **适用范围**: 三节点集群 (41/58/111)

---

## 节点专属配置文件

每个节点有独立的 `docker-compose.node-XX.yml` 文件：

| 节点 | 配置文件 | 服务数 |
|:----:|----------|:------:|
| 41 | `docker-compose.node-41.yml` | 8 |
| 58 | `docker-compose.node-58.yml` | 4 |
| 111 | `docker-compose.node-111.yml` | 3 |

**使用方法**:
```bash
# Server 41
docker-compose -f docker-compose.node-41.yml up -d

# Server 58
docker-compose -f docker-compose.node-58.yml up -d

# Server 111
docker-compose -f docker-compose.node-111.yml up -d
```

---

## 容器部署矩阵

| 容器 | Server 41 | Server 58 | Server 111 | 说明 |
|:-----|:---------:|:---------:|:----------:|:-----|
| **基础设施** |
| `microservice-stock-clickhouse` | ✅ | ✅ | ✅ | 三副本复制 |
| `microservice-stock-mootdx-api` | ✅ | ✅ | ✅ | 本地行情源 |
| `microservice-stock-mootdx-source` | ✅ | ✅ | ✅ | gRPC 行情 |
| **应用服务 (仅 41)** |
| `task-orchestrator` | ✅ | ❌ | ❌ | 任务调度 |
| `quant-strategy-dev` | ✅ | ❌ | ❌ | 策略引擎 |
| `get-stockdata-api-dev` | ✅ | ❌ | ❌ | 数据 API |
| `microservice-stock-snapshot-recorder` | ✅ | ❌ | ❌ | 快照记录 |
| **监控 (仅 41)** |
| `microservice-stock-prometheus` | ✅ | ❌ | ❌ | 指标采集 |
| `microservice-stock-grafana` | ✅ | ❌ | ❌ | 可视化 |
| **支撑服务 (仅 41)** |
| `microservice-stock-redis` | ✅ | ❌ | ❌ | 缓存 |
| `microservice-stock-rabbitmq` | ✅ | ❌ | ❌ | 消息队列 |
| `microservice-stock-nacos` | ✅ | ❌ | ❌ | 服务发现 |
| **开发工具 (仅 58)** |
| `microservice-stock-gitlab` | ❌ | ✅ | ❌ | 代码仓库 |

---

## 各节点配置详情

### Server 41 (192.168.151.41) - 主控节点

**角色**: 主控 + 开发 + 监控

**启动容器** (10 个):
```bash
docker-compose -f docker-compose.yml up -d \
  clickhouse mootdx-api mootdx-source \
  task-orchestrator quant-strategy get-stockdata \
  prometheus redis rabbitmq nacos
```

**环境变量** (`.env`):
```bash
SHARD_INDEX=0
SHARD_TOTAL=3
CLICKHOUSE_HOST=localhost
MOOTDX_API_URL=http://localhost:8003
```

---

### Server 58 (192.168.151.58) - 计算节点

**角色**: 计算 + GitLab

**启动容器** (4 个):
```bash
# ClickHouse (系统服务)
systemctl status clickhouse-server

# 应用容器
docker-compose up -d mootdx-api mootdx-source

# GitLab (独立启动)
docker start microservice-stock-gitlab
```

**环境变量** (`.env`):
```bash
SHARD_INDEX=1
SHARD_TOTAL=3
CLICKHOUSE_HOST=localhost
MOOTDX_API_URL=http://localhost:8003
```

---

### Server 111 (192.168.151.111) - 计算节点

**角色**: 计算

**启动容器** (3 个):
```bash
# ClickHouse (系统服务)
systemctl status clickhouse-server

# 应用容器
docker-compose up -d mootdx-api mootdx-source
```

**环境变量** (`.env`):
```bash
SHARD_INDEX=2
SHARD_TOTAL=3
CLICKHOUSE_HOST=192.168.151.111
MOOTDX_API_URL=http://localhost:8003
```

---

## 快速操作

### 启动分片采集

```bash
# Server 41
docker-compose run --rm gsd-worker python -m jobs.sync_tick --scope all

# Server 58
ssh bxgh@192.168.151.58 "cd ~/microservice-stock && docker-compose run --rm gsd-worker python -m jobs.sync_tick --scope all"

# Server 111
ssh bxgh@192.168.151.111 "cd ~/microservice-stock && docker-compose run --rm gsd-worker python -m jobs.sync_tick --scope all"
```

### 清理不需要的容器

```bash
# 从 Server 41 执行
./scripts/cleanup_worker_nodes.sh
```

---

## 相关文档

- [三节点架构](../architecture/infrastructure/THREE_NODE_ARCHITECTURE.md)
- [运维手册](./RUNBOOK.md)
- [代码同步策略](./CODE_SYNC_STRATEGY.md)

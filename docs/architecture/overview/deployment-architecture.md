# 部署架构

> **更新时间**: 2026-01-08  
> **架构**: 三节点集群 (Server 41/58/111)

---

## 集群拓扑

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         三节点集群部署架构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Server 41 (主控)          Server 58 (计算)        Server 111 (计算)       │
│   192.168.151.41           192.168.151.58          192.168.151.111         │
│   ┌───────────────┐        ┌───────────────┐       ┌───────────────┐       │
│   │ ClickHouse    │◄──────►│ ClickHouse    │◄─────►│ ClickHouse    │       │
│   │ Keeper ID:1   │        │ Keeper ID:2   │       │ Keeper ID:3   │       │
│   │               │        │               │       │               │       │
│   │ task-orch     │        │ GitLab        │       │               │       │
│   │ quant-strategy│        │               │       │               │       │
│   │ get-stockdata │        │               │       │               │       │
│   │ gsd-worker    │        │ gsd-worker    │       │ gsd-worker    │       │
│   │ mootdx-api    │        │ mootdx-api    │       │ mootdx-api    │       │
│   │ Redis         │        │               │       │               │       │
│   │ Prometheus    │        │               │       │               │       │
│   └───────────────┘        └───────────────┘       └───────────────┘       │
│        SHARD=0                 SHARD=1                 SHARD=2             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 服务部署矩阵

| 服务 | 41 | 58 | 111 | 说明 |
|:-----|:--:|:--:|:---:|:-----|
| **基础设施** |
| ClickHouse | ✅ | ✅ | ✅ | 三副本复制 |
| Keeper | ✅ | ✅ | ✅ | Raft 共识 |
| mootdx-api | ✅ | ✅ | ✅ | 本地行情源 |
| Redis | ✅ | ❌ | ❌ | 单点缓存 |
| **应用服务** |
| task-orchestrator | ✅ | ❌ | ❌ | 单点调度 |
| quant-strategy | ✅ | ❌ | ❌ | 策略引擎 |
| get-stockdata | ✅ | ❌ | ❌ | 数据 API |
| gsd-worker | ✅ | ✅ | ✅ | 分片采集 |
| **监控** |
| Prometheus | ✅ | ❌ | ❌ | 指标采集 |
| Grafana | ✅ | ❌ | ❌ | 可视化 |
| **开发工具** |
| GitLab | ❌ | ✅ | ❌ | 代码仓库 |

---

## 环境变量配置

每个节点的 `.env` 差异点：

| 变量 | Server 41 | Server 58 | Server 111 |
|------|:---------:|:---------:|:----------:|
| `SHARD_INDEX` | 0 | 1 | 2 |
| `SHARD_TOTAL` | 3 | 3 | 3 |
| `CLICKHOUSE_HOST` | localhost | localhost | 192.168.151.111 |

---

## 代码同步策略

```
                    ┌─────────────────────┐
                    │   GitLab (Server 58)│
                    │  192.168.151.58:8800│
                    └──────────┬──────────┘
                               │ git pull
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
      Server 41           Server 58           Server 111
      (开发)              (计算)              (计算)
```

- **代码**: Git 统一管理
- **配置**: `.env` 本地独立

---

## 相关文档

- [三节点架构详解](../infrastructure/THREE_NODE_ARCHITECTURE.md)
- [ClickHouse 复制集群](../infrastructure/clickhouse-replicated-cluster.md)
- [代码同步策略](../../operations/CODE_SYNC_STRATEGY.md)

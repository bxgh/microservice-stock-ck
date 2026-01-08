# microservice-stock 架构文档

> **更新时间**: 2026-01-08  
> **当前架构**: 三节点集群 (Server 41/58/111)

---

## 📚 文档索引

### 系统概览 (`overview/`)

| 文档 | 说明 |
|------|------|
| [high-level-architecture.md](overview/high-level-architecture.md) | 高层架构图 |
| [tech-stack.md](overview/tech-stack.md) | 技术栈选型 |
| [deployment-architecture.md](overview/deployment-architecture.md) | 部署架构 |

### 基础设施 (`infrastructure/`)

| 文档 | 说明 |
|------|------|
| [clickhouse-replicated-cluster.md](infrastructure/clickhouse-replicated-cluster.md) | ClickHouse 三节点复制集群 ⭐ |
| [database-schema.md](infrastructure/database-schema.md) | 数据库表结构 |
| [internal-network-setup.md](infrastructure/internal-network-setup.md) | 内网配置 |
| [SERVER_HARDWARE_ARCHITECTURE.md](infrastructure/SERVER_HARDWARE_ARCHITECTURE.md) | 服务器硬件架构 ⭐ |

### 服务架构 (`services/`)

| 文档 | 说明 |
|------|------|
| [get-stockdata-architecture.md](services/get-stockdata-architecture.md) | get-stockdata 核心服务 |
| [mootdx-source.md](services/mootdx-source.md) | Mootdx 数据源 |
| [akshare-source.md](services/akshare-source.md) | AKShare 数据源 |

### 领域模型 (`domain/`)

| 文档 | 说明 |
|------|------|
| [domain-tick.md](domain/domain-tick.md) | 分笔数据领域 |
| [domain-kline.md](domain/domain-kline.md) | K线数据领域 |
| [domain-finance.md](domain/domain-finance.md) | 财务数据领域 |
| [domain-strategy.md](domain/domain-strategy.md) | 策略领域 |

### 开发规范 (`standards/`)

| 文档 | 说明 |
|------|------|
| [coding-standards.md](standards/coding-standards.md) | 编码规范 |
| [error-handling-strategy.md](standards/error-handling-strategy.md) | 错误处理策略 |
| [ADR-001-data-source-microservices.md](standards/ADR-001-data-source-microservices.md) | 架构决策记录 |

### 归档文档 (`archive/`)

历史版本和暂未实现的设计文档，详见 [archive/README.md](archive/README.md)

---

## 🏗️ 当前架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         三节点集群架构                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Server 41 (主控)          Server 58 (计算)        Server 111 (计算)       │
│   ┌───────────────┐         ┌───────────────┐       ┌───────────────┐       │
│   │ ClickHouse    │◄───────►│ ClickHouse    │◄─────►│ ClickHouse    │       │
│   │ Keeper ID:1   │         │ Keeper ID:2   │       │ Keeper ID:3   │       │
│   │               │         │               │       │               │       │
│   │ task-orch     │         │ GitLab        │       │               │       │
│   │ quant-strategy│         │               │       │               │       │
│   │ gsd-worker    │         │ gsd-worker    │       │ gsd-worker    │       │
│   └───────────────┘         └───────────────┘       └───────────────┘       │
│        SHARD=0                  SHARD=1                 SHARD=2             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 相关文档

| 类型 | 位置 |
|------|------|
| 运维文档 | [docs/operations/](../operations/) |
| AI 上下文 | [docs/ai_context/](../ai_context/) |
| 进度报告 | [docs/reports/](../reports/) |

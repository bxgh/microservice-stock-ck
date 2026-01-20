# 任务调度系统架构设计

> 本目录包含任务调度系统的完整架构设计文档。

## 文档目录

| 文档 | 说明 |
|:-----|:-----|
| [00_overview.md](./00_overview.md) | 总体概述与核心决策 |
| [01_current_issues.md](./01_current_issues.md) | 当前问题分析 |
| [02_target_architecture.md](./02_target_architecture.md) | 目标架构设计 (初版) |
| [03_smart_collection.md](./03_smart_collection.md) | 智能采集框架 |
| [04_implementation_roadmap.md](./04_implementation_roadmap.md) | 实施路线图 |
| **[05_final_architecture.md](./05_final_architecture.md)** | **最终确认方案** ⭐ |
| [06_orchestrator_design.md](./06_orchestrator_design.md) | Task Orchestrator 详细设计 |
| [07_gsd_shared_design.md](./07_gsd_shared_design.md) | GSD-Shared 共享库设计 |
| [09_service_split_plan.md](./09_service_split_plan.md) | 服务拆分详细建议 |
| [11_kline_sync_optimization.md](./11_kline_sync_optimization.md) | K线同步优化方案 |
| [12_architecture_principles.md](./12_architecture_principles.md) | 核心架构原则 |
| **[13_command_driven_architecture.md](./13_command_driven_architecture.md)** | **3.0 指令驱动分布式架构** 💎 |

## 核心结论 (已确认 v2)

1. **2+1 服务架构**：gsd-api (长驻) + gsd-worker (临时) + task-orchestrator
2. **合并 sync/quality**：gsd-worker 包含同步、质量检测、修复
3. **临时任务模式**：worker 用完即销毁
4. **3节点分片**：tick 数据采集 3 节点分布式并行采集
5. **兼容层保留**：get-stockdata 保留原样，新服务验证后废弃

---

### 分布式部署概览

| 节点 | 运行服务 | 主要任务 |
|:-----|:---------|:---------|
| **Server 41** | `task-orchestrator` | **主调度中心**: 负责所有任务的定时发射与协调 |
| **Server 58** | `shard-poller (Shard 1)` | **执行节点**: 认领并执行 ID/Shard 对应的指令 |
| **Server 111** | `shard-poller (Shard 2)` | **执行节点**: 认领并执行 ID/Shard 对应的指令 |

> [!TIP]
> **配置整合 (v3.0)**: 58/111 节点不再维护独立的 `tasks_58.yml`，而是共享并挂载主节点的 `tasks.yml`。

---

### 📊 数据同步任务

| 任务ID | 名称 | 调度时间 | 类型 | 状态 |
|:-------|:-----|:---------|:-----|:-----|
| `daily_stock_collection` | 每日股票代码采集 | 08:45 每日 | cron | ✅ 已启用 |
| `daily_kline_sync` | K线每日同步 | 17:30 交易日 | trading_cron | ✅ 已启用 |
| `tick_data_migrate` | 分笔数据归档 | 09:00 交易日 | http | ✅ 已启用 |
| `distributed_tick_sync` | 分笔同步(分布式指令) | 18:00 交易日 | command_emitter | ✅ 架构 3.0 |

#### 分片执行分配 (通过指令)

| 节点 | 角色 | 过滤规则 (Shard) | 说明 |
|:-----|:-------|:-----|:---------|
| Server 41 | Master/Worker 0 | 0 或 NULL | 处理全局及分片 0 任务 |
| Server 58 | Worker 1 | 1 | 处理分配至分片 1 的任务 |
| Server 111 | Worker 2 | 2 | 处理分配至分片 2 的任务 |

---

### 📈 策略任务

| 任务ID | 名称 | 调度时间 | 类型 | 状态 |
|:-------|:-----|:---------|:-----|:-----|
| `daily_strategy_scan` | 每日策略扫描 | 20:30 交易日 | docker | ✅ 已启用 |
| `weekly_backtest` | 周末策略回测 | 08:00 周日 | docker | ⚠️ 待实现 |

---

### 🔧 系统维护任务

| 任务ID | 名称 | 调度时间 | 类型 | 状态 |
|:-------|:-----|:---------|:-----|:-----|
| `daily_db_backup` | 数据库备份 | 03:00 每日 | docker | ✅ 已启用 |
| `daily_cache_warmup` | 缓存预热 | 09:00 交易日 | http | ✅ 已启用 |
| `weekly_log_cleanup` | 日志清理 | 02:00 周日 | docker | ✅ 已启用 |
| `weekly_clickhouse_log_cleanup` | ClickHouse日志清理 | 03:00 周日 | http | ✅ 已启用 |

---

### ✅ 数据质量任务

| 任务ID | 名称 | 调度时间 | 类型 | 状态 |
|:-------|:-----|:---------|:-----|:-----|
| `weekly_deep_audit` | 每周深度审计 | 02:00 周日 | docker | ⚠️ 待实现 |
| `monthly_audit` | 月度数据审计 | 03:00 每月5号 | docker | ⚠️ 待实现 |

---

## 时间线可视化

```
每日调度时间线 (交易日):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   03:00       08:45    09:00          15:30      17:30   18:30   19:00
     │           │        │              │          │       │       │
     ▼           ▼        ▼              ▼          ▼       ▼       ▼
 数据库备份   股票采集  数据归档       分笔采集    K线同步  策略扫描  质量门禁
                                      (3节点并行)
每周调度时间线 (周日):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   02:00      03:00
     │          │
     ▼          ▼
 日志清理   ClickHouse清理
```

---

**创建时间**: 2026-01-02  
**最后更新**: 2026-01-20

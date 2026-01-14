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

## 核心结论 (已确认 v2)

1. **2+1 服务架构**：gsd-api (长驻) + gsd-worker (临时) + task-orchestrator
2. **合并 sync/quality**：gsd-worker 包含同步、质量检测、修复
3. **临时任务模式**：worker 用完即销毁
4. **3节点分片**：tick 数据采集 3 节点分布式并行采集
5. **兼容层保留**：get-stockdata 保留原样，新服务验证后废弃

---

## 当前定时任务清单 (2026-01-14 更新)

### 分布式部署概览

| 节点 | 配置文件 | 主要任务 |
|:-----|:---------|:---------|
| **Server 41** | `tasks.yml` | 主调度节点，包含全部任务类型 |
| **Server 58** | `tasks_58.yml` | 分片任务节点 (Shard-1) |
| **Server 111** | `tasks_111.yml` | 分片任务节点 (Shard-2) |

---

### 任务分类统计

| 分类 | 已启用 | 待实现 | 合计 |
|:-----|:------:|:------:|:----:|
| 📊 数据同步 | 4 | 2 | 6 |
| 📈 策略任务 | 1 | 1 | 2 |
| 🔧 系统维护 | 5 | 0 | 5 |
| ✅ 数据质量 | 0 | 2 | 2 |
| **合计** | **10** | **5** | **15** |

---

### 📊 数据同步任务

| 任务ID | 名称 | 调度时间 | 类型 | 状态 |
|:-------|:-----|:---------|:-----|:-----|
| `daily_stock_collection` | 每日股票代码采集 | 09:05 每日 | cron | ✅ 已启用 |
| `daily_kline_sync` | K线每日同步 | 17:30 交易日 | trading_cron | ✅ 已启用 |
| `tick_data_migrate` | 分笔数据归档 | 09:00 交易日 | http | ✅ 已启用 |
| `daily_tick_sync_shard_0` | 盘后分笔采集(Shard-0) | 15:35 交易日 | workflow | ✅ 已启用 |
| `weekly_financial_sync` | 财务数据更新 | 06:00 周六 | docker | ⚠️ 待实现 |
| `monthly_valuation_sync` | 估值数据更新 | 06:00 每月1号 | docker | ⚠️ 待实现 |

#### 分布式分笔采集

| 节点 | 任务ID | 分片 | 配置文件 |
|:-----|:-------|:-----|:---------|
| Server 41 | `daily_tick_sync_shard_0` | Shard-0 | tasks.yml |
| Server 58 | `daily_tick_sync_shard_1` | Shard-1 | tasks_58.yml |
| Server 111 | `daily_tick_sync_shard_2` | Shard-2 | tasks_111.yml |

---

### 📈 策略任务

| 任务ID | 名称 | 调度时间 | 类型 | 状态 |
|:-------|:-----|:---------|:-----|:-----|
| `daily_strategy_scan` | 每日策略扫描 | 18:30 交易日 | docker | ✅ 已启用 |
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
   03:00                        09:00      09:05          15:35      17:30   18:30
     │                            │          │              │          │       │
     ▼                            ▼          ▼              ▼          ▼       ▼
 数据库备份               数据归档+预热   股票采集       分笔采集    K线同步  策略扫描
                                
每周调度时间线 (周日):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   02:00      03:00
     │          │
     ▼          ▼
 日志清理   ClickHouse清理
```

---

**创建时间**: 2026-01-02  
**最后更新**: 2026-01-14

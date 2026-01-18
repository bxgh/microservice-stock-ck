# Task Orchestrator 任务调度清单

本文档列出了当前系统配置的所有定时任务及其调度时间。

## 0. 多节点任务分配矩阵 (防止调度冲突)

为了确保分布式环境下的任务不重复、不冲突，各节点分工如下：

| 任务类别 | Node 41 (核心/监控) | Node 58 (计算 1) | Node 111 (计算 2) |
| :--- | :---: | :---: | :---: |
| **核心维护** (代码采集/备份/清理/归档) | ✅ **主控** | ❌ 禁用 | ❌ 禁用 |
| **数据门禁** (Pre-Market Gate) | ✅ **主测** | ❌ 禁用 | ❌ 禁用 |
| **K线同步** | ✅ **全量** | ❌ 禁用 | ❌ 禁用 |
| **分笔同步 (分片)** | ❌ 禁用 (Cron) | ✅ Shard 1 | ✅ Shard 2 |
| **策略扫描** | ✅ 启用 | ❌ 禁用 | ❌ 禁用 |
| **常驻采集** (快照/分笔) | ✅ 运行 (41) | - | - |

---

## 1. 核心运行任务 (已启用)

| 任务 ID | 任务名称 | 调度源头 | 调度规律 | 预计时间 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `daily_stock_collection` | **每日代码采集** | **Orchestrator** | `45 8 * * *` | 08:45 | 拉取全市场股票清单 |
| `tick_data_migrate` | **分笔数据归档** | **Orchestrator** | `0 9 * * 1-5` | 09:00 | 归档并清空当日表 |
| `pre_market_gate` | **盘前质量门禁** | **Orchestrator** | `15 9 * * 1-5` | 09:15 | 名单校验与准入 |
| `daily_cache_warmup` | **缓存预热** | **Orchestrator** | `20 9 * * 1-5` | 09:20 | 提升 API 速度 |
| `daily_tick_sync` | **分笔同步(全分片)** | **Linux Cron** | `35 16 * * 1-5` | 16:35 | 分节点(41/58/111)并行同步 |
| `daily_kline_sync` | **K线每日同步** | **Orchestrator** | `30 17 * * *` | 17:30 | 智能增量同步 (自愈模式) |
| `daily_strategy_scan` | **每日策略扫描** | **Orchestrator** | `30 18 * * 1-5` | 18:30 | 计算选股信号 |
| `post_market_gate` | **盘后大门禁** | **Orchestrator** | `18 19 * * 1-5` | 19:18 | 深度审计与触发修复 |
| `daily_db_backup` | **数据库备份** | **Orchestrator** | `0 3 * * *` | 03:00 | 核心数据备份 |
| `weekly_log_cleanup` | **日志清理** | **Orchestrator** | `0 2 * * 0` | 周日 02:00 | 清理旧日志 |

---

## 2. 补采与修复任务 (按需触发)

这些任务通常由 `CommandPoller` 监听指令执行，不执行固定 Cron 调度。

| 任务 ID | 任务名称 | 发起源头 | 说明 |
| :--- | :--- | :--- | :--- |
| `repair_kline` | **K线数据修复** | **PostMarketGate (Auto)** | 审计失败时自动触发自愈 |
| `repair_tick` | **分笔数据补采** | **PostMarketGate (Auto)** | 缺分钟记录超过 100 时触发 |
| `collect_tick_sharded` | **分笔指定日期分片采集** | **SQL / Frontend / Manual** | 指定日期的分片采集，支持参数化 |
| `stock_data_supplement` | **定向个股数据补充** | **SQL / Frontend / Manual** | 针对特定股票的多种数据类型补充 |
| `adhoc_audit` | **专项重新审计** | **SQL / Manual** | 手动下发 `post_market_audit` 指令 |

---

## 3. 待启用/开发中任务

| 任务 ID | 任务名称 | 预设调度 | 状态 |
| :--- | :--- | :--- | :--- |
| `weekly_financial_sync` | 财务数据更新 | 每周六 06:00 | ❌ 已禁用 |
| `monthly_valuation_sync` | 估值数据更新 | 每月1号 06:00 | ❌ 已禁用 |
| `weekly_backtest` | 周末策略回测 | 每周日 08:00 | ❌ 已禁用 |
| `weekly_deep_audit` | 每周深度审计 | 每周日 02:00 | ❌ 已禁用 |
| `monthly_audit` | 月度数据审计 | 每月5号 03:00 | ❌ 已禁用 |

> [!TIP]
> **TradingCron** 任务会自动跳过法定节假日和周末。如果需要临时手动执行某个任务，可以通过 Orchestrator 的 `/trigger` 接口下发指令。

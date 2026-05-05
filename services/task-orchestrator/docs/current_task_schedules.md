# Task Orchestrator 任务调度清单

本文档列出了当前系统配置的所有定时任务及其调度时间。

## 0. 多节点任务分配矩阵 (防止调度冲突)

为了确保分布式环境下的任务不重复、不冲突，各节点分工如下：

| 任务类别 | Node 41 (核心/监控) | Node 58 (计算 1) | Node 111 (计算 2) |
| :--- | :---: | :---: | :---: |
| **核心维护** (代码采集/备份/清理/归档) | ✅ **主控** | ❌ 禁用 | ❌ 禁用 |
| **数据门禁** (Pre-Market Gate) | ✅ **主测** | ❌ 禁用 | ❌ 禁用 |
| **K线同步** | ✅ **全量** | ❌ 禁用 | ❌ 禁用 |
| **分笔同步 (集中全量)** | ✅ **Node 41 采集** | ❌ 禁用 (测试用途) | ❌ 禁用 (测试用途) |
| **策略扫描** | ✅ 启用 | ❌ 禁用 | ❌ 禁用 |
| **常驻采集** (快照/分笔) | ✅ 运行 (41) | - | - |

---


## 1. 核心运行任务 (已启用)

| 任务 ID | 任务名称 | 调度源头 | 调度规律 | 预计时间 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `trigger_pre_market_workflow` | **盘前 4.0 准备管线** | **Orchestrator** | `45 8 * * 1-5` | 08:45 | 自动触发 `pre_market_prep_4.0` (归档 -> 采集 -> 门禁) |
| `noon_market_gate` | **午间数据质量门禁** | **Orchestrator** | `0 12 * * 1-5` | 12:00 | 盘中自愈触发器 |
| `trigger_post_market_workflow` | **盘后 4.0 自愈管线** | **Orchestrator** | `30 15 * * 1-5` | 15:30 | 自动触发 `post_market_audit` (审计 -> 修复 -> 策略) |
| `daily_kline_sync` | **K线每日同步** | **Orchestrator** | `30 17 * * 1-5` | 17:30 | 盘后自愈管线逻辑外部同步 |
| `daily_db_backup` | **数据库备份** | **Orchestrator** | `0 3 * * *` | 03:00 | 核心数据备份 |
| `weekly_log_cleanup` | **日志清理** | **Orchestrator** | `0 2 * * 0` | 周日 02:00 | 清理旧日志 |

> [!NOTE]
> **架构 4.0 更新 (2026-02-04)**:  
> 1. **配置模块化**: `tasks.yml` 已拆分为 `main.yml` + `tasks/*.yml` 目录结构，支持动态扩展。
> 2. **管线驱动**: 大多数原子任务（如 `daily_strategy_scan`, `tick_data_migrate`）已取消独立调度，改由 Workflow 管理。
> 3. **提前审计**: 盘后自愈管线 `trigger_post_market_workflow` 已提前至 **15:30**。

---

## 2. 补采与修复任务 (按需触发)

这些任务通常由 `CommandPoller` 监听指令执行，或由 Workflow 驱动，不执行固定 Cron 调度。

| 任务 ID | 任务名称 | 发起源头 | 说明 |
| :--- | :--- | :--- | :--- |
| `calculate_data_quality` | **计算数据质量** | **post_market_audit** | 4.0 核心审计任务 (L1-L3 Audit) |
| `stock_data_supplement` | **定向个股数据补充** | **Workflow / Manual** | 针对特定股票的多种数据类型补充 |
| `repair_tick` | **分笔数据补采** | **Manual** | 手动启动全量/指定日期重采样 |
| `trigger_historical_recovery`| **历史分笔治理管线**| **Manual** | 针对历史空洞进行专项治理 |

---

## 3. 待启用/开发中任务

| 任务 ID | 任务名称 | 预设调度 | 状态 |
| :--- | :--- | :--- | :--- |
| `ai_quality_gatekeeper` | AI 质量门禁 | Workflow 探测 | ⚠️ 待完善 (SiliconFlow API) |
| `weekly_financial_sync` | 财务数据更新 | 每周六 06:00 | ❌ 已禁用 |
| `monthly_valuation_sync` | 估值数据更新 | 每月1号 06:00 | ❌ 已禁用 |
| `weekly_backtest` | 周末策略回测 | 每周日 08:00 | ❌ 已禁用 |

> [!TIP]
> **TradingCron** 任务会自动跳过法定节假日和周末。如果需要临时手动执行某个任务，可以通过 Orchestrator 的 API 接口下发指令。

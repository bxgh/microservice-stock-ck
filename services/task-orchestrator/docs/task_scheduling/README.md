# 任务调度系统架构设计 (Orchestrator 2.0 / Architecture 4.0)

> 本目录包含任务调度系统的完整架构设计文档。

## 文档目录

| 文档 | 说明 |
|:-----|:-----|
| [00_overview.md](./00_overview.md) | 总体概述与核心决策 |
| [05_final_architecture.md](./05_final_architecture.md) | **最终确认方案** ⭐ |
| [06_orchestrator_design.md](./06_orchestrator_design.md) | Task Orchestrator 详细设计 |
| [13_command_driven_architecture.md](./13_command_driven_architecture.md) | **3.0 指令驱动分布式架构** 💎 |
| [14_modular_config_4.0.md](./14_modular_config_4.0.md) | **4.0 模块化任务编排 (新)** � |

## 核心结论 (v4.0 演进)

1. **模块化配置结构**：
   - `main.yml`: 全局环境、镜像、挂载与通知配置。
   - `tasks/*.yml`: 按功能领域（同步、策略、维护、触发器）拆分的任务定义。
2. **从“定时任务”向“自愈管线”转型**：
   - 绝大多数业务任务已取消独立 Cron 调度，由 Workflow 控制。
   - 依赖关系通过 `depends_on` 和 `DAGEngine` 在内存中闭环执行。
3. **提前审计窗口**：
   - 盘后审计管线从 `17:30` 提前至 **`15:30`**，旨在收盘后第一时间发现并修复数据缺失。
4. **统一 Context 传递**：执行日期等关键参数由 Trigger 统一注入，杜绝各任务日期计算不一致。

---

### 📊 核心调度任务

| 任务ID | 名称 | 调度时间 | 类型 | 状态 |
|:-------|:-----|:---------|:-----|:-----|
| `trigger_pre_market_workflow` | 盘前准备管线 (4.0) | 08:45 | workflow_trigger | ✅ 已启用 |
| `noon_market_gate` | 午间质量门禁 | 12:00 | workflow_trigger | ✅ 已启用 |
| `trigger_post_market_workflow` | 盘后自愈管线 (4.0) | 15:30 | workflow_trigger | ✅ 已启用 |
| `daily_kline_sync` | K线同步 | 17:30 | trading_cron | ✅ 已启用 |
| `daily_db_backup` | 核心数据库备份 | 03:00 | cron | ✅ 已启用 |

---

## 时间线可视化 (Architecture 4.0)

```
每日调度时间线 (交易日):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   03:00       08:45    12:00          15:30      17:30   18:00
     │           │        │              │          │       │
     ▼           ▼        ▼              ▼          ▼       ▼
  数据库备份   盘前管线  午间门禁       盘后管线    K线同步  备用同步
             (归档/采集) (自愈)       (审计/策略)
```

---

**创建时间**: 2026-01-02  
**最后更新**: 2026-02-04 (Architecture 4.0)

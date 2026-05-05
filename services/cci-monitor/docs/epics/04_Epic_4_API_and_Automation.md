# Epic 4: API 扩展与自动化调度

## 目标
暴露计算结果并确保系统每日自动运行。

## Stories

### Story 4.1: 核心 API 端点实现
- **端点**：`/api/v1/cci/latest`, `/api/v1/cci/history`。
- **要求**：支持按日期和层级过滤。

### Story 4.2: 自动化调度器 (APScheduler)
- **实现**：`src/scheduler/main.py`。
- **触发**：交易日 17:00 自动触发 `DailyService.run_daily()`。

### Story 4.3: 预警推送 (Notifier)
- **实现**：支持 Server 酱或钉钉，当 CCI 超过阈值（如 > 1.3）时发送推送。

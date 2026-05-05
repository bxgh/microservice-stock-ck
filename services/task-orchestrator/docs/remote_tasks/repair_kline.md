# K线数据按日补采 (repair_kline)

## 1. 任务概述

`repair_kline` 用于触发日线数据的按日同步与校验。它采用“智能自愈”模式，能自动检测缺失的数据并进行补全，同时也包含复权因子的同步。

*   **Task ID**: `repair_kline`
*   **服务**: `gsd-worker`
*   **执行入口**: `jobs.sync_kline`

## 2. 核心参数

通过 `task_commands.params` JSON 字段传递参数：

| 参数名 | 必填 | 类型 | 说明 | 示例 |
|:---|:---|:---|:---|:---|
| `date` | 是 | String | 目标日期 (YYYYMMDD) | `"20260115"` |

## 3. 执行逻辑

### 3.1 智能自愈同步
容器启动后执行 `jobs.sync_kline`:

1.  **模式识别**: 识别到传入 `date` 参数，启动智能自愈模式。
2.  **差异比对**: 对比 Redis（实时源）与 ClickHouse（已存储）的 K 线数据。
3.  **增量更新**: 仅对缺失或不一致的 K 线进行写入/更新操作。
4.  **复权因子**: 任务结束前会自动检查并更新当天的复权因子数据。

### 3.2 自动联动 (Auto Linkage)
`repair_kline` 任务在 `CommandPoller` 层配置了自动联动规则：
*   **前置任务**: `repair_kline` 执行成功 (`DONE`)
*   **自动触发**: `post_market_gate` (盘后门禁审计)
*   **目的**: 确保补采后的数据质量符合标准，自动生成质量报告。

## 4. 触发示例

### SQL 触发

```sql
-- 触发 2026-01-15 的 K 线数据检查与修复
INSERT INTO task_commands (task_id, params) 
VALUES ('repair_kline', '{"date": "20260115"}');
```

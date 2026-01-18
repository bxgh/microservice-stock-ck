# 远程校验触发器 (Validation Trigger)

该任务允许通过 API 手动触发特定日期的 Gate-3 全市场审计逻辑，并将结果持久化到云端 MySQL。

## 1. 任务定义

- **Task ID**: `trigger_validation`
- **Worker Script**: `services/gsd-worker/src/jobs/trigger_validation.py`
- **Type**: `docker`

## 2. API 调用方式

通过 `task-orchestrator` 的 API 触发：

```bash
POST /api/v1/tasks/trigger_validation/trigger
Content-Type: application/json

{
    "params": {
        "date": "2026-01-18"  // 必填: 目标审计日期
    }
}
```

## 3. 执行逻辑

1. 接收 API 传入的 `date` 参数（格式 `YYYY-MM-DD`）。
2. 初始化 `PostMarketGateService`。
3. 调用 `run_gate_check(date_str=...)` 执行审计：
   - **K线覆盖率**: 对比 ClickHouse 与 Tencent Cloud MySQL。
   - **分笔覆盖率**: 基于 MySQL 有 K 线的股票统计。
   - **连续性检查**: 检查 9:25-15:00 完整性。
   - **一致性抽检**: 随机抽取股票对比价格与成交量。
4. 生成 `ValidationResult` (Market Level)。
5. 将结果写入 MySQL `data_audit_summaries` 和 `data_audit_details` 表。

## 4. 数据库结果查询

```sql
SELECT * FROM alwaysup.data_audit_summaries 
WHERE data_type='market' AND trade_date='2026-01-18';
```

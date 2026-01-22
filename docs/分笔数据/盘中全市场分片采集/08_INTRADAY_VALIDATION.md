# 盘中分笔数据校验与补采系统 (08_INTRADAY_VALIDATION.md)

## 1. 系统背景
盘中分笔采集采用三节点分布式实时流式采集。由于网络波动或 TDX 节点不稳定，可能导致部分个股数据缺失或采集不全。
本校验系统作为“数据保险层”，在交易时段的特定时刻自动检索全局覆盖情况，并触发靶向补采。

## 2. 核心架构与逻辑

### 2.1 全局视图校验 (Global Visibility)
在分布式环境下，单个节点只能看到自己的 `_local` 表。校验任务通过 ClickHouse **分布式表 (`tick_data_intraday`)** 进行查询：
- **逻辑**: 计算 `(Redis 预期的全市场股票总数) vs (分布式表中实际存在的股票数)`。
- **关键修复**: 所有的校验逻辑必须通过分布式表视图进行，避免 Master 节点因看不到其他节点的分片数据而产生误判，导致疯狂重复补采。

### 2.2 靶向补采逻辑 (Targeted Repair)
当检测到覆盖率低于设定阈值（默认 95%）或存在明确缺失时，触发补采：
1. **查重 (Idempotency)**: 补采前调用 `check_quality`。
   - 如果是当日，查询 `tick_data_intraday`。
   - 如果是历史，查询 `tick_data`。
2. **分布式写入 (Distributed Write)**: 补采任务抓取到的数据**必须写入分布式表**，而非本地表。由 ClickHouse 负责将数据均匀散列到 41、58、111 节点。
3. **低频股优化**: 将判定股票存在的门槛设定为 `count() >= 1`。只要库里有记录，即认为 API 访问过且成功，不再反复补采交易极不活跃的个股。

## 3. 任务调度配置

系统在 `tasks.yml` 中配置了两个一体化任务（校验 + 补采）：

| 任务 ID | 执行时间 | 描述 | 目标表 |
| :--- | :--- | :--- | :--- |
| `intraday_tick_validation_noon` | 11:35 | **午休校验**: 检查 9:25-11:30 的覆盖情况并补齐 | `tick_data_intraday` |
| `intraday_tick_validation_close` | 15:05 | **盘后校验**: 检查全天数据完整性并执行最终补齐 | `tick_data_intraday` |

## 4. 关键组件与 Job

- **Job 脚本**: `services/gsd-worker/src/jobs/intraday_tick_validation.py`
- **校验类**: `libs/gsd-shared/gsd_shared/validation/tick_validator.py`
  - 核心方法: `check_intraday_coverage()`, `check_quality()`
- **写入类**: `services/gsd-worker/src/core/tick_writer.py`
  - 导出目标: `target_table = "tick_data_intraday"`

## 5. 手动运维指令

### 5.1 手动触发校验 (Dry-run)
```bash
docker run --rm --network host gsd-worker:latest \
  python -m jobs.intraday_tick_validation --session close --dry-run
```

### 5.2 历史数据覆盖率检查 (指定日期)
```bash
docker run --rm --network host gsd-worker:latest \
  python -m jobs.intraday_tick_validation --session close --date 20260121 --dry-run
```

### 5.3 检查数据重复情况 (SQL)
```sql
-- 检查某只股票是否有非预期的重复入库
SELECT stock_code, count() 
FROM stock_data.tick_data_intraday 
WHERE trade_date = '2026-01-21' 
GROUP BY stock_code 
ORDER BY count() DESC LIMIT 10;
```

## 6. 审计与 observability

所有的校验结果会通过 `save_audit_summary` 记录：
- **日志记录**: 控制台输出 `Coverag: XX.X% (Missing: N)`。
- **MySQL 审计**: 记录至 `alwaysup.data_audit_summaries`。
- **重复报警**: 如果同一日期补采后数据量依然异常堆积（如分笔数 > 2万），需检查 TDX 数据源质量。

---
**更新日期**: 2026-01-22  
**维护者**: Quant Engineering Team

# 数据门禁 (Gate-3): 盘后深度审计与对账

## 1. 目标
在收盘且所有采集完成后 (19:18)，进行最严格的"数据大考"：
1. **K线数据一致性校验** - 确认本地 ClickHouse K线数据与云端 MySQL 基准数据 100% 对齐。
2. **分笔时段完整性检查** - 深度检查所有股票是否覆盖 09:25-15:00 无断点（标准 241 分钟）。
3. **价格一致性对账** - 比对分笔数据与日 K 线收盘价，确保存储逻辑无偏差。
4. **异常自动恢复** - 发现数据不一致时，自动触发"先删后补"的自愈逻辑。

## 2. 核心校验逻辑
- **K线覆盖率 (云端对齐)**:
    - 基准: 查询云端 MySQL 当日 `stock_kline_daily` 记录总数。
    - 实测: 查询本地 ClickHouse 当日 `stock_kline_daily` 记录总数。
    - 公式: `覆盖率 = ClickHouse 计数 / MySQL 计数 * 100%`。
    - 优势: 自动忽略停牌股票，无需维护静态名单。
- **分笔连续性审计**: 聚合分笔数据，统计每只股票的分钟数、首笔时间及末笔时间。
- **价格对账规则**: 抽样核心标的，校验 K 线 `close_price` 与分笔最后一笔 `price` 的差值 (< 0.011)。

## 3. 自动化联动流程 (Self-Healing Loop)

Gate-3 审计完成后，系统会根据检测结果自动触发对应的修复任务：

| 检测项 | 判定条件 | 触发任务 |
| :--- | :--- | :--- |
| K线覆盖率 | < 100% | `daily_kline_sync` |
| 分笔覆盖率 | < 95% | `repair_tick` |
| 时段缺失股票数 | > 100 | `repair_tick` |

### 3.1 K线自愈同步
当 K 线覆盖率低于阈值时，系统执行以下自愈逻辑：
1. 对比 ClickHouse 与 MySQL 的当日记录数。
2. 若不一致，物理删除 ClickHouse 中当日数据 (`ALTER TABLE ... DELETE`)。
3. 重新从云端拉取缺失数据。

### 3.2 分笔补采
当分笔覆盖率或时段完整性异常时，系统自动触发 `repair_tick` 任务，对缺失时段进行定向补采。

### 3.3 手动触发
除自动修复外，也可通过 SQL 指令手动触发特定任务：

**重新执行盘后审计：**
```sql
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES ('post_market_audit', '{"date": "20260115"}', 'PENDING');
```

**手动触发 K 线补采：**
```sql
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES ('repair_kline', '{"date": "20260115"}', 'PENDING');
```

**手动触发分笔补采：**
```sql
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES ('repair_tick', '{"date": "20260115"}', 'PENDING');
```

## 4. 技术实现细节

### 4.1 Orchestrator 隔离执行
- **环境隔离**: 审计逻辑通过 `gsd-worker` 独立容器运行。
- **云端连接**: 计算结果通过 SSH 隧道实时同步至云端 MySQL。

### 4.2 多表智能切换
- 审计逻辑能够自动识别当前日期，对于当日审计优先使用 `tick_data_intraday` 表，确保实时性。

### 4.3 审计持久化
审计结果最终写入云端 `alwaysup.data_gate_audits` 表，支持分布式查看。

| 字段 | 说明 |
| :--- | :--- |
| `trade_date` | 当前交易日 |
| `gate_id` | `GATE_3` |
| `is_complete` | `1`: 全项通过, `0`: 异常 |
| `description` | `K线覆盖率:100% 分笔覆盖率:98% 时段缺失:5` (详细结果) |

## 5. 常见问题处理
- **K线覆盖率不足**: 检查 `daily_kline_sync` 任务状态，或手动触发 `repair_kline`。
- **分笔时段缺失**: 通常由网络波动导致，系统会自动触发 `repair_tick` 补采。
- **对账失败**: 通常由收盘集合竞价的秒级延迟引起，会自动重试。

## 6. 开发状态
- K线云端对齐逻辑开发完成
- 分笔连续性深度审计开发完成
- 价格一致性对账逻辑开发完成
- 自愈修复联动开发完成

## 7. 完成时间
- 2026-01-15
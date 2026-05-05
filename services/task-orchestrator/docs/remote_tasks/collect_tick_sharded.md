# 分笔指定日期分片采集 (collect_tick_sharded)

## 1. 任务概述

`collect_tick_sharded` 是专为分布式架构设计的原子级采集任务。与 `repair_tick` 不同，它**不包含自动拆分逻辑**，而是用于精确执行指定日期、指定分片的数据采集。通常用于底层调度或对特定分片的定向修复。

*   **Task ID**: `collect_tick_sharded`
*   **服务**: `gsd-worker`
*   **执行入口**: `jobs.sync_tick`

## 2. 核心参数

通过 `task_commands.params` JSON 字段传递参数：

| 参数名 | 必填 | 类型 | 说明 | 示例 |
|:---|:---|:---|:---|:---|
| `date` | 是 | String | 目标采集日期 (YYYYMMDD) | `"20260115"` |
| `shard_index` | 否 | Int | 分片索引 (0/1/2)，用于本地计算分片归属 | `1` |
| `shard_id` | 否 | Int | 别名，同 `shard_index` | `1` |
| `distributed_source` | 否 | String | 数据源模式，默认 `none` | `"none"` |

## 3. 执行逻辑

容器启动后执行 `jobs.sync_tick`:

1.  **参数接收**: 接收 `--date` 和 `--shard-index`。
2.  **源确认** (`distributed_source=none`): 
    *   **优先**: 尝试查询 `kline_data_local` 表中指定日期的**实际交易股票列表**。
        *   这确保了补采范围精准覆盖了当天有成交的股票，避免无效请求。
    *   **降级**: 如果 K 线数据不可用，则降级为读取本地/配置文件的静态全量名单。
3.  **本地分片过滤**: 
    *   获取到全量列表后，在本地使用 `xxHash64` 算法计算每只股票的分片 ID。
    *   仅保留 `hash(code) % 3 == shard_index` 的股票。
4.  **采集执行**: 对过滤后的股票进行采集和写入。

## 4. 与 repair_tick 的区别

| 特性 | repair_tick | collect_tick_sharded |
|:---|:---|:---|
| **面向对象** | 业务管理员 (补采) | 系统调度 / 高级运维 |
| **智能拆分** | ✅ 支持 (股票数>1666自动拆分) | ❌ 不支持 (原子执行) |
| **股票来源** | K线表 (优先) -> 本地名单 | K线表 (优先) -> 本地名单 |
| **适用场景** | "补采某天数据", "补采某几只股票" | "重跑 Shard 1", "分布式计划任务" |

## 5. 触发示例

### SQL 触发

```sql
-- 场景: 手动重跑 2026-01-15 的 Shard 1 分片任务
INSERT INTO task_commands (task_id, params) 
VALUES ('collect_tick_sharded', '{"date": "20260115", "shard_index": 1}');
```

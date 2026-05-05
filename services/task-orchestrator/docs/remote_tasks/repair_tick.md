# 分笔数据按日补采 (repair_tick)

## 1. 任务概述

`repair_tick` 是一个用于远程触发分笔数据补采的专用任务。它支持按日期、按股票列表进行精确补采，并内置了智能分片机制以应对大规模补采需求。

*   **Task ID**: `repair_tick`
*   **服务**: `gsd-worker`
*   **执行入口**: `jobs.sync_tick`

## 2. 核心参数

通过 `task_commands.params` JSON 字段传递参数，支持以下字段：

| 参数名 | 必填 | 类型 | 说明 | 示例 |
|:---|:---|:---|:---|:---|
| `date` | 是 | String | 目标补采日期 (YYYYMMDD) | `"20260115"` |
| `stock_codes` | 否 | Array/String | 指定补采的股票代码列表（不传则默认为全市场） | `["000001", "600519"]` 或 `"000001,600519"` |
| `shard_id` | 否 | Int | (内部使用) 指定执行的分片 ID | `0` |

## 3. 执行逻辑

### 3.1 智能分片 (Smart Splitting)
当 `CommandPoller` 收到 `repair_tick` 任务时，会根据 `stock_codes` 的数量触发智能逻辑：

1.  **少量补采 (Num <= 1666)**:
    直接在当前节点（Shard 0）启动容器执行补采。

2.  **大批量/全量补采 (Num > 1666)**:
    *   Poller 会拦截当前任务。
    *   自动将其拆分为 3 个子任务，分别带有 `shard_id: 0`, `shard_id: 1`, `shard_id: 2` 参数。
    *   重新插入 `task_commands` 队列。
    *   分布式集群中的各节点（Server 41/58/111）领取各自的分片任务并行执行。

### 3.2 容器执行 (Docker)
`gsd-worker` 容器启动后执行 `jobs.sync_tick`:

1.  **解析日期**: 使用传入的 `--date`。
2.  **确定范围**:
    *   如果有 `--stock-codes`: 仅采集指定股票。
    *   如果有 `--shard-index`: 从全市场中通过哈希计算过滤属于该分片的股票。
3.  **执行采集**: 调用 `TickSyncService` 执行采集、清洗、写入 ClickHouse。

## 4. 触发示例

### SQL 触发

```sql
-- 场景1: 补采特定几只股票
INSERT INTO task_commands (task_id, params) 
VALUES ('repair_tick', '{"date": "20260115", "stock_codes": ["300067", "600525"]}');

-- 场景2: 全量补采某日数据 (将自动通过智能分片在集群间并行执行)
INSERT INTO task_commands (task_id, params) 
VALUES ('repair_tick', '{"date": "20260115"}');
```

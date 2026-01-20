# 指令队列格式规范 (task_commands)

本文档定义了前端或外部系统向 **AlwaysUp** 任务指令队列下达命令时的标准格式。

## 1. 数据库表结构 (Schema)
目标数据库：`alwaysup`  
目标表名：`task_commands`

| 字段名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| **`task_id`** | `VARCHAR(64)` | 是 | 后端任务标识符 (见下表) |
| **`params`** | `JSON` | 是 | 参数字典，包含执行逻辑和路由信息 |
| **`status`** | `ENUM` | 是 | 固定写入 `'PENDING'`，等待后端抓取 |
| **`result`** | `TEXT` | 否 | 执行结果或错误日志 (由后端回写) |

### 1.1 Params 中的路由参数 (Architecture 3.0)
在指令驱动架构下，`params` 中可以包含用于任务分发的字段。如果未指定，默认由 Node 41 (Shard 0) 执行。

| 参数名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **`shard_id`** / **`shard_index`** | `INT` | 指定该任务由哪个节点处理 (0: Node 41, 1: Node 58, 2: Node 111) |

## 2. 标准指令内容 (Commands)

| 业务场景 | `task_id` | `params` 示例 | 执行效果 |
| :--- | :--- | :--- | :--- |
| **指定分片采集** | `collect_tick_sharded` | `{"date": "20260120", "shard_id": 1}` | 指定由 Node 58 采集该分片的 Tick 数据 |
| **全量分片发射** | `distributed_tick_sync` | `{}` | **Emitter**: 主节点自动生成 3 条 PENDING 指令分发给各节点 |
| **同步股票名单** | `daily_stock_collection` | `{}` | 强制同步全量名单镜像到 Redis |
| **补采分笔数据** | `repair_tick` | `{"date": "20260115"}` | 重新抓取指定日期的 Tick 数据 |
| **补采日线 K 线** | `repair_kline` | `{"date": "20260115"}` | 重新抓取指定日期的日 K 线数据 |
| **手动门禁 (Gate-1)** | `pre_market_gate` | `{}` | 立即重新核对名单/心跳，更新 Gate-1 状态 |
| **手动门禁 (Gate-3)** | `post_market_gate` | `{}` | 立即重新核对覆盖率/一致性，更新 Gate-3 状态 |

## 3. 指令生命周期状态
前端可根据 `status` 字段实现 UI 逻辑：
- **`PENDING`**: (前端写入) 指令已入队，等待处理。
- **`RUNNING`**: (后端更新) 任务正在内网容器中执行。
- **`DONE`**: (后端更新) 指令执行成功。
- **`FAILED`**: `status = 'FAILED'`: 提示“修复失败”，展示 `result` 字段中的错误详情。

## 5. 自动化联动 (Scheme A)
为了提升体验，后端已实现以下功能：
- 当 `daily_stock_collection` 执行成功时，会自动触发 `pre_market_gate` 的重新审计。
- 当 `repair_tick` 或 `repair_kline` 执行成功时，会自动触发 `post_market_gate` 的重新审计。
- **这意味着修复完成后，前端大盘的状态卡片通常会在一分钟内自动转绿。**

## 4. SQL 插入示例 (参考)
```sql
-- 示例：触发补采 2026-01-15 的分笔数据
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES (
    'repair_tick', 
    '{"date": "20260115"}', 
    'PENDING'
);

-- 示例：触发同步股票名单
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES (
    'daily_stock_collection', 
    '{}', 
    'PENDING'
);
```

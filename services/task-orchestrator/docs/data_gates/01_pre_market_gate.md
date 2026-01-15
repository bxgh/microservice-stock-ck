# 数据门禁 (Gate-1): 盘前准入与名单校验

## 1. 目标
在每个交易日开盘前 (09:15)，确保系统具备新一交易日的运行条件：
1. **股票名单同步 (核心P0)** - 检查全市场股票名单（上市、退市、停牌）是否已同步为最新，防止遗漏新股或采集已退市个股。
2. **Redis 采集队列校验** - 验证 Redis 中的采集名单与数据库是否一致。
3. **系统环境就绪** - 快速检测 ClickHouse、Redis 连接状态。
4. **昨日状态核验** - 检查昨日盘后审计 (Gate-3) 是否完成，确保无遗留补采任务。

## 2. 核心校验逻辑
- **名单核对**: 比较云端权威名单数量与本地库/Redis 数量。
- **系统心跳**: 通过 `PING` 指令确认关键存储组件的可达性。
- **昨日准入**: 查询 `data_gate_audits` 表中昨日 `GATE_3` 的完成状态。

## 3. 自动化联动流程 (One-Click Repair Loop)
这是本系统的核心特性，实现了“发现 -> 修复 -> 自动更新”的闭环。

### 方案 A：自动重审 (Auto-Trigger)
- **触发源**: 当 `daily_stock_collection` (名单同步任务) 运行成功时。
- **动作**: `task-orchestrator` 会立即触发一次 `pre_market_gate` 的重新审计。
- **结果**: 修复完成后，前端看板的状态会在 1 分钟内自动从红转绿。

### 方案 B：手动触发 (Manual Trigger)
- **SQL 指令**: 前端通过向 `task_commands` 写入指令实现手动重审。
```sql
INSERT INTO alwaysup.task_commands (task_id, params, status) 
VALUES ('pre_market_gate', '{}', 'PENDING');
```

## 4. 技术实现细节

### 4.1 Orchestrator 隔离执行
- **环境隔离**: 门禁通过 `gsd-worker` 独立容器运行。
- **源码挂载**: 容器启动时会自动挂载最新的 `/app/src`，确保逻辑随时热更新。

### 4.2 审计持久化
审计结果最终写入云端 `alwaysup.data_gate_audits` 表，支持分布式查看。

| 字段 | 说明 |
| :--- | :--- |
| `trade_date` | 当前交易日 |
| `gate_id` | `GATE_1` |
| `is_complete` | `1`: 全项通过, `0`: 异常 |
| `description` | `股票代码:OK 心跳:OK 昨日数据:FAIL` (详细结果) |

## 5. 常见问题处理
- **名单不一致**: 触发 `daily_stock_collection` 任务。
- **昨日审计 FAIL**: 说明昨日有数据缺失且未完成补采，需核对 `GATE_3` 的详细报告。

## 6. 开发状态
- 门禁逻辑开发完成
- 自动触发机制开发完成
- 手动触发机制开发完成  

## 7. 完成时间
- 2026-01-15    

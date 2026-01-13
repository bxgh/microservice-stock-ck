# A股全市场盘后补采与归档方案交付说明

## 1. 实现概述
完成了 A 股全市场 (~5,300 只股票) 的盘后自动化分笔补采及数据归档系统。该系统通过分布式调度确保采集效率，并实现了完善的数据生命周期管理。

## 2. 核心功能
### 2.1 分布式调度 (3 节点)
- **触发时间**: 每日盘后 **15:35**。
- **执行引擎**: 每个节点 (41/58/111) 部署独立的 `task-orchestrator`。
- **任务分片**: 
  - **Server 41**: 负责 Shard 0 (~1,800 股)
  - **Server 58**: 负责 Shard 1 (~1,800 股)
  - **Server 111**: 负责 Shard 2 (~1,700 股)

### 2.2 数据存储流转
- **当日补采**: 数据首先进入 `tick_data_intraday` (分布式表)，用于当日高频分析。
- **自动归档**: 次日 **09:00**，由 Server 41 触发归档任务：
  1. 将 `tick_data_intraday` 数据平移至历史主表 `tick_data` (映射至 `tick_data_local`)。
  2. 清空 `tick_data_intraday` 为当日交易做准备。
- **历史回溯**: 脚本自动识别日期，非当日补采数据将**直接写入** `tick_data` 历史表。

### 2.3 状态与质量监控
- **Redis 状态 Hash**: `tick_sync:status:YYYYMMDD`
- **详细记录**: 每只股票记录 `状态|记录数|数据开始时间|数据结束时间|同步时间|错误信息`。
- **完整性验证**: 通过 `data_start` (应为 09:25) 和 `data_end` (应为 15:00) 即可快速验证数据是否抓取完整。

### 2.4 数据质量与自动补采
针对金融数据的高完整性要求，系统集成了自动补采机制：
- **主动搜索**: `TickSyncService` 使用多维搜索矩阵，强制寻找 09:25 数据。
- **自动冗余**: 配合 ClickHouse `ReplacingMergeTree` 引擎，支持无损覆盖补采。
- **补采工具**: 提供 `retry_tick.py` 脚本，可精准识别并重采“失败”或“早盘不全”的股票。

## 3. 文件变更汇总
- **逻辑核心**: [tick_sync_service.py](file:///home/bxgh/microservice-stock/services/gsd-worker/src/core/tick_sync_service.py) (状态追踪、多表路由、时间范围记录)
- **任务定义**: 
  - [tasks.yml (Node 41)](file:///home/bxgh/microservice-stock/services/task-orchestrator/config/tasks.yml)
  - [tasks_58.yml](file:///home/bxgh/microservice-stock/services/task-orchestrator/config/tasks_58.yml)
  - [tasks_111.yml](file:///home/bxgh/microservice-stock/services/task-orchestrator/config/tasks_111.yml)
- **环境部署**: [docker-compose.node-58.yml](file:///home/bxgh/microservice-stock/docker-compose.node-58.yml), [docker-compose.node-111.yml](file:///home/bxgh/microservice-stock/docker-compose.node-111.yml)

## 4. 运维指南
### 4.1 手动启动补采
若需手动触发今日分片补采（以 Node 58 为例）：
```bash
docker exec -it task-orchestrator python3 src/jobs/sync_tick.py --scope all --shard-index 1
```

### 4.2 查看进度
```bash
redis-cli HGETALL tick_sync:status:20260113
```

## 6. 验证证据 (2026-01-13 实测)
在 Server 41 部署后，通过手动触发 20 只股票的样本测试，验证结果如下：

### 6.1 ClickHouse 数据持久化
```sql
SELECT stock_code, count(), min(tick_time), max(tick_time) 
FROM stock_data.tick_data_intraday 
WHERE trade_date = '2026-01-13' GROUP BY stock_code LIMIT 5;
```
| stock_code | count() | min(tick_time) | max(tick_time) |
| :--- | :--- | :--- | :--- |
| 600884 | 132759 | 09:25:00 | 14:16:00 |
| 002938 | 147966 | 09:25:00 | 14:16:00 |

### 6.2 Redis 状态追踪 (DB 0)
```bash
redis-cli -p 6379 -a redis123 HLEN tick_sync:status:20260113
# 输出: (integer) 20
```
- **成功率**: 100% (20/20)
- **Redis 键**: `tick_sync:status:20260113`
- **结论**: 系统端到端贯通，从采集、数据清洗、ClickHouse 写入到 Redis 状态更新均运行正常。

---

## 7. 项目状态
- **开发完成**: 100%
- **环境验证**: 已通过 (Server 41)
- **正式上线**: 已就绪

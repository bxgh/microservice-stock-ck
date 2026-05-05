# Task Orchestrator (任务调度中心)

负责整个系统的任务调度与协调，基于 APScheduler 实现，支持 Docker 容器任务、HTTP 请求任务以及复杂的工作流（DAG）。

## 核心功能

- **统一调度**: 集中管理所有定时任务 (Cron/Interval/Date)。
- **交易日历**: 支持 `trading_cron` 类型，仅在 A 股交易日触发。
- **任务类型**:
    - `docker`: 启动/运行 Docker 容器命令。
    - `http`: 发送 HTTP 请求 (Webhook/API 调用)。
    - `workflow`: 串行/并行执行一组子任务 (DAG)。
- **失败重试**: 内置指数退避重试机制。

## 配置

任务定义文件位于 `config/tasks.yml`。

### 关键配置项
- **每日股票代码采集**: 09:05 运行，负责抓取全市场股票并进行分片 (Sharding) 计算。
- **K线每日同步**: 17:30 运行，自适应并发同步。
- **分笔数据采集 (Shard 0)**: 16:35 运行，负责本节点的 Tick 数据采集。

## 分布式架构

Task Orchestrator 是分布式 Tick 数据采集架构的核心组件之一：

1.  **分片计算**: 调度 `jobs.daily_stock_collection` 计算并分发分片元数据到 Redis。
2.  **Shard 0 执行**: 直接调度本地的 `jobs.sync_tick` (Shard 0)。
3.  **协同**: 远程节点 (Server 58/111) 通过 Crontab/Systemd 独立运行 Shard 1 和 Shard 2，共享 Orchestrator 生成的 Redis 元数据。

详细架构设计请参考: [Tick Data Distributed Sharding Implementation](../../docs/architecture/tick_data_sharding_implementation.md)

## 运行

```bash
# 启动调度器
docker-compose up -d task-orchestrator

# 查看日志
docker-compose logs -f task-orchestrator
```

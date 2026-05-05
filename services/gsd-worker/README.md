# GSD-Worker

股票数据处理任务执行器 - 临时任务模式

## 功能

- K线数据同步 (支持分片并行)
- 盘后分笔数据同步 (支持分布式 Sharding)
- 每日股票代码采集 (元数据管理)
- 数据质量检测
- 数据修复

## 分布式架构

关于分笔数据采集的分布式 Sharding 实现，请参考架构文档:
[Tick Data Distributed Sharding Implementation](../../docs/architecture/tick_data_sharding_implementation.md)

## 运行

### 本地运行

```bash
# 同步任务
python src/jobs/sync_kline.py

# 分片同步 (4个分片中的第1个)
python src/jobs/sync_kline.py --shard 0 --total 4

# 质量检测
python src/jobs/quality_check.py

# 股票代码采集 (每日 09:05)
python src/jobs/daily_stock_collection.py

# 分笔数据同步 (例如 Shard 0)
python src/jobs/sync_tick.py --scope all --shard-index 0 --shard-total 3

```

### Docker运行

```bash
# 同步任务
docker run --rm gsd-worker python -m jobs.sync_kline

# 分片同步
docker run --rm gsd-worker python -m jobs.sync_kline --shard 0 --total 4

# 质量检测
docker run --rm gsd-worker python -m jobs.quality_check

# 分笔数据同步
docker run --rm --net=host gsd-worker python -m jobs.sync_tick --scope all --shard-index 0 --shard-total 3

```

## 依赖

- gsd-shared (共享数据模型)
- MySQL (源数据)
- ClickHouse (目标数据)
- Redis (锁+状态)

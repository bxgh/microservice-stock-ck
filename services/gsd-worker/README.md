# GSD-Worker

股票数据处理任务执行器 - 临时任务模式

## 功能

- K线数据同步 (支持分片并行)
- 数据质量检测
- 数据修复

## 运行

### 本地运行

```bash
# 同步任务
python src/jobs/sync_kline.py

# 分片同步 (4个分片中的第1个)
python src/jobs/sync_kline.py --shard 0 --total 4

# 质量检测
python src/jobs/quality_check.py
```

### Docker运行

```bash
# 同步任务
docker run --rm gsd-worker python -m jobs.sync_kline

# 分片同步
docker run --rm gsd-worker python -m jobs.sync_kline --shard 0 --total 4

# 质量检测
docker run --rm gsd-worker python -m jobs.quality_check
```

## 依赖

- gsd-shared (共享数据模型)
- MySQL (源数据)
- ClickHouse (目标数据)
- Redis (锁+状态)

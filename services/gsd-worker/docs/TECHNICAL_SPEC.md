# GSD-Worker 技术规范

> **版本**: 1.0  
> **服务类型**: 临时任务执行器  
> **运行模式**: Docker 容器 (一次性)

---

## 1. 服务定位

**gsd-worker** 是从 get-stockdata 拆分出的**数据处理任务执行器**，负责：
- K线数据同步 (MySQL → ClickHouse)
- 数据质量检测
- 数据修复
- 支持分片并行执行

**不包含**：查询API（由 gsd-api 负责）

---

## 2. 任务清单

| 任务 | 入口文件 | 功能 | 执行频率 |
|:-----|:---------|:-----|:---------|
| **K线同步** | `jobs/sync_kline.py` | MySQL → ClickHouse 增量同步 | 每日 18:00 |
| **质量检测** | `jobs/quality_check.py` | 数据完整性、一致性检查 | 每日 19:00 |
| **数据修复** | `jobs/repair_data.py` | 修复缺失/异常数据 | 按需触发 |

---

## 3. 运行模式

### 3.1 临时容器模式

```bash
# 单次执行后自动销毁
docker run --rm gsd-worker python -m jobs.sync_kline

# 执行流程
1. 容器启动
2. 执行任务
3. 输出日志
4. 容器销毁
```

### 3.2 分片并行模式

```bash
# 4个容器并行同步，每个处理 1/4 股票
docker run --rm gsd-worker python -m jobs.sync_kline --shard 0 --total 4
docker run --rm gsd-worker python -m jobs.sync_kline --shard 1 --total 4
docker run --rm gsd-worker python -m jobs.sync_kline --shard 2 --total 4
docker run --rm gsd-worker python -m jobs.sync_kline --shard 3 --total 4

# 优势：
# - 原本 2小时 → 30分钟
# - 资源按需分配
# - 失败隔离
```

---

## 4. 核心服务

### 4.1 KLineSyncService

**位置**: `src/core/sync_service.py`

**功能**:
- 智能增量同步 (基于 ClickHouse 最大日期)
- 全量同步
- 按股票代码同步
- 按时间戳同步

**关键方法**:
```python
async def sync_smart_incremental():
    """智能增量同步 - 默认模式"""
    
async def sync_full():
    """全量同步 - 初始化用"""
    
async def sync_by_stock_codes(codes: list):
    """按股票同步 - 修复用"""
```

### 4.2 DataQualityService

**位置**: `src/core/data_quality_service.py`

**功能**:
- 完整性检查 (缺失日期检测)
- 一致性检查 (异常值检测)
- 生成质量报告

---

## 5. 分片逻辑实现

### 5.1 分片策略

```python
# jobs/sync_kline.py
async def main(shard_index: int = 0, total_shards: int = 1):
    service = KLineSyncService()
    await service.initialize()
    
    if total_shards > 1:
        # 获取所有股票列表
        all_stocks = await get_all_stock_codes()
        
        # 按 hash 分片
        my_stocks = [
            code for code in all_stocks
            if hash(code) % total_shards == shard_index
        ]
        
        logger.info(f"分片 {shard_index}/{total_shards}: {len(my_stocks)} 只股票")
        
        # 只同步分配给我的股票
        await service.sync_by_stock_codes(my_stocks)
    else:
        # 单机模式
        await service.sync_smart_incremental()
```

### 5.2 分片参数传递

```bash
# 通过命令行参数
python -m jobs.sync_kline --shard 0 --total 4

# 或通过环境变量
SHARD_INDEX=0 TOTAL_SHARDS=4 python -m jobs.sync_kline
```

---

## 6. 数据流转

### 6.1 同步流程

```
1. MySQL 查询
   ↓
   SELECT code, trade_date, open, high, low, close, volume, amount
   FROM stock_kline_daily
   WHERE trade_date > (ClickHouse 最大日期)
   
2. 数据转换
   ↓
   from gsd_shared.models import KLineRecord
   records = [KLineRecord.from_mysql(row) for row in rows]
   
3. ClickHouse 插入
   ↓
   INSERT INTO stock_kline_daily VALUES
   (records[0].to_clickhouse_dict(), ...)
   
4. 状态更新
   ↓
   Redis: sync:status = "success"
   MySQL: sync_execution_logs 记录
```

### 6.2 错误处理

```python
try:
    await sync_service.sync_smart_incremental()
    return 0  # 成功退出码
except Exception as e:
    logger.error(f"同步失败: {e}", exc_info=True)
    await notify_failure(e)  # 发送告警
    return 1  # 失败退出码
```

---

## 7. 技术要求

### 7.1 并发安全

```python
class KLineSyncService:
    def __init__(self):
        self._lock = asyncio.Lock()  # 保护共享状态
        self.mysql_pool = None
        self.clickhouse_pool = None
```

### 7.2 资源管理

```python
async def main():
    service = KLineSyncService()
    await service.initialize()
    
    try:
        await service.sync_smart_incremental()
    finally:
        await service.close()  # 确保清理
```

### 7.3 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def fetch_from_mysql():
    # 自动重试 3 次
    pass
```

---

## 8. 环境配置

### 8.1 Docker 配置

```yaml
# docker-compose.yml (task-orchestrator 调用)
services:
  gsd-worker-sync:
    image: gsd-worker:latest
    command: python -m jobs.sync_kline --shard 0 --total 4
    environment:
      # MySQL (源数据)
      - MYSQL_HOST=192.168.151.18
      - MYSQL_PORT=3306
      - MYSQL_USER=stock_user
      - MYSQL_PASSWORD=***
      - MYSQL_DATABASE=stock_data
      
      # ClickHouse (目标数据)
      - CLICKHOUSE_HOST=localhost
      - CLICKHOUSE_PORT=9000
      - CLICKHOUSE_USER=admin
      - CLICKHOUSE_PASSWORD=***
      - CLICKHOUSE_DB=stock_data
      
      # Redis (锁+状态)
      - REDIS_HOST=localhost
      - REDIS_PORT=6379
    network_mode: host
    restart: "no"  # 一次性任务，不重启
```

### 8.2 资源限制

```yaml
services:
  gsd-worker-sync:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
```

---

## 9. 监控与日志

### 9.1 日志格式

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 关键日志点
logger.info(f"启动K线同步任务 (分片 {shard_index+1}/{total_shards})")
logger.info(f"进度: {synced:,}/{total:,} ({progress:.1f}%)")
logger.info(f"✓ 同步完成，共 {synced:,} 条记录")
```

### 9.2 执行记录

```sql
-- MySQL: sync_execution_logs
INSERT INTO sync_execution_logs (
    task_name,
    status,
    total_records,
    duration_seconds,
    error_message,
    created_at
) VALUES (
    'kline_sync',
    'SUCCESS',
    12345,
    120.5,
    NULL,
    NOW()
);
```

### 9.3 Redis 状态

```python
# 实时状态
await redis.set("sync:kline:status", json.dumps({
    "status": "running",
    "progress": 45.2,
    "message": "同步中: 5000/11000",
    "updated_at": "2024-01-02 18:15:30"
}), ex=3600)
```

---

## 10. 性能优化

### 10.1 批量插入

```python
# 批量大小
BATCH_SIZE = 10000

# 分批插入
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i+BATCH_SIZE]
    await clickhouse_client.execute(
        "INSERT INTO stock_kline_daily VALUES",
        [r.to_clickhouse_dict() for r in batch]
    )
```

### 10.2 连接池配置

```python
# MySQL 连接池
mysql_pool = await aiomysql.create_pool(
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    minsize=1,
    maxsize=5  # 临时任务不需要太多连接
)

# ClickHouse 连接池
clickhouse_pool = await asynch.create_pool(
    host=CLICKHOUSE_HOST,
    port=CLICKHOUSE_PORT,
    minsize=1,
    maxsize=3
)
```

---

## 11. 开发检查清单

### 任务入口
- [ ] 支持命令行参数 (--shard, --total)
- [ ] 实现分片逻辑
- [ ] 返回正确退出码 (0=成功, 1=失败)
- [ ] 添加详细日志

### 核心服务
- [ ] 使用 `asyncio.Lock` 保护共享状态
- [ ] 实现 `initialize()` 和 `close()`
- [ ] 添加重试机制
- [ ] 错误处理完整

### 数据模型
- [ ] 使用 `gsd_shared.models`
- [ ] 实现 `from_mysql()` 转换
- [ ] 实现 `to_clickhouse_dict()` 转换

### 资源管理
- [ ] 连接池正确配置
- [ ] 资源清理 (`finally` 块)
- [ ] 内存使用可控

### 监控
- [ ] 日志输出完整
- [ ] 执行记录写入 MySQL
- [ ] Redis 状态更新

---

## 12. 参考文档

- [sync_service.py](file:///home/bxgh/microservice-stock/services/get-stockdata/src/core/sync_service.py) - 同步服务实现
- [data_quality_service.py](file:///home/bxgh/microservice-stock/services/get-stockdata/src/core/data_quality_service.py) - 质量检测实现
- [gsd-shared 设计](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/architecture/task_scheduling/07_gsd_shared_design.md) - 数据模型
- [CODING_STANDARDS.md](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/CODING_STANDARDS.md) - 编码规范

---

**维护**: 随 gsd-worker 开发同步更新  
**版本**: 1.0 (2026-01-02)

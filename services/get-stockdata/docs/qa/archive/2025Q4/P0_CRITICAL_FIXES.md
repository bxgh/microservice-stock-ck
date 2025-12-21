# P0 Critical Fixes - Quick Reference

本文档提供 P0 级别问题的具体修复代码，可直接应用。

---

## Fix 1: QuotesService 并发安全 (Thread Safety)

**文件**: `services/get-stockdata/src/data_services/quotes_service.py`

### 需要修改的代码

在 `__init__` 方法中添加锁：

```python
def __init__(
    self,
    cache_manager: Optional[CacheManager] = None,
    enable_cache: bool = True,
    timeout: int = 20,
):
    self._cache_manager = cache_manager
    self._enable_cache = enable_cache
    self._timeout = timeout
    self._initialized = False
    self._lock = asyncio.Lock()
    
    self._snapshot_cache: Optional[pd.DataFrame] = None
    self._snapshot_ts: float = 0
    self._snapshot_lock = asyncio.Lock()  # ← ADD THIS LINE
    self._snapshot_ttl: float = 30.0
    
    from concurrent.futures import ThreadPoolExecutor
    self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="QuotesAkShare")
```

在所有访问 `_snapshot_cache` 和 `_snapshot_ts` 的地方添加锁保护：

```python
async def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
    """获取实时行情"""
    # Check if snapshot is fresh
    async with self._snapshot_lock:  # ← PROTECT READ
        cache_age = time.time() - self._snapshot_ts
        if self._snapshot_cache is not None and cache_age < self._snapshot_ttl:
            # Use cached snapshot
            return self._filter_snapshot(self._snapshot_cache, codes)
    
    # Need to refresh
    await self._refresh_snapshot()
    
    async with self._snapshot_lock:  # ← PROTECT READ AGAIN
        return self._filter_snapshot(self._snapshot_cache, codes)

async def _refresh_snapshot(self):
    """刷新快照缓存"""
    try:
        new_data = await self._fetch_from_akshare()
        
        async with self._snapshot_lock:  # ← PROTECT WRITE
            self._snapshot_cache = new_data
            self._snapshot_ts = time.time()
            
    except Exception as e:
        logger.error(f"Failed to refresh snapshot: {e}")
```

---

## Fix 2: QuotesService 资源清理 (Resource Cleanup)

**文件**: `services/get-stockdata/src/data_services/quotes_service.py`

### 添加 close() 方法

在 `QuotesService` 类中添加以下方法：

```python
async def close(self) -> None:
    """关闭服务并清理所有资源
    
    清理顺序:
    1. 关闭线程池
    2. 关闭缓存管理器
    3. 重置标志
    """
    logger.info("Closing QuotesService...")
    
    # 1. Shutdown executor
    if hasattr(self, '_executor') and self._executor is not None:
        try:
            self._executor.shutdown(wait=True, cancel_futures=True)
            logger.info("✅ QuotesService executor shut down")
        except Exception as e:
            logger.error(f"Error shutting down executor: {e}")
    
    # 2. Close cache manager
    if self._cache_manager is not None:
        try:
            await self._cache_manager.close()
            logger.info("✅ QuotesService cache manager closed")
        except Exception as e:
            logger.error(f"Error closing cache manager: {e}")
    
    # 3. Reset state
    self._initialized = False
    async with self._snapshot_lock:
        self._snapshot_cache = None
        self._snapshot_ts = 0
    
    logger.info("✅ QuotesService closed")
```

### 在 main.py 的 lifespan 中调用 close()

确保在 `main.py` 的 shutdown 阶段调用 `close()`：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... startup code ...
    
    yield
    
    # Shutdown phase
    logger.info("🛑 Starting graceful shutdown...")
    
    # Close QuotesService
    if hasattr(app.state, 'quotes_service') and app.state.quotes_service:
        await app.state.quotes_service.close()
    
    # Close other services...
    if hasattr(app.state, 'financial_service') and app.state.financial_service:
        await app.state.financial_service.close()
    
    logger.info("✅ Shutdown complete")
```

---

## Fix 3: 删除重复的 except 块

**文件**: `services/get-stockdata/src/main.py`

### 定位代码 (约第 627-630 行)

找到以下代码：

```python
    try:
        if config_manager:
            await config_manager.watch()
        logger.info("✅ Config manager initialized and watching")
    except Exception as e:
        logger.warning(f"⚠️ Config manager not available: {e}")
    except Exception as e:  # ← DELETE THIS LINE
        logger.warning(f"⚠️ Config manager not available: {e}")  # ← DELETE THIS LINE
```

### 修复后的代码

删除重复的 except 块：

```python
    try:
        if config_manager:
            await config_manager.watch()
        logger.info("✅ Config manager initialized and watching")
    except Exception as e:
        logger.warning(f"⚠️ Config manager not available: {e}")
```

---

## 验证修复

### 1. 运行代码质量检查

```bash
cd /home/bxgh/microservice-stock/services/get-stockdata
/code_quality_check
```

### 2. 运行并发测试

创建测试文件后运行：

```bash
docker compose -f docker-compose.dev.yml run --rm get-stockdata \
  pytest tests/test_quotes_service_concurrency.py -v
```

### 3. 检查资源泄漏

启动服务并监控线程数：

```bash
# 终端 1: 启动服务
docker compose up get-stockdata

# 终端 2: 监控线程数
watch -n 1 'docker stats get-stockdata --no-stream'

# 终端 3: 发送请求
for i in {1..100}; do
  curl http://localhost:8000/api/v1/quotes/realtime?codes=600519,000001
done

# 终端 1: 优雅停止
docker compose stop get-stockdata

# 检查是否有线程残留
docker compose ps -a
```

---

## Checklist

- [ ] Fix 1: QuotesService 添加 `_snapshot_lock`
- [ ] Fix 1: 所有 snapshot 访问都使用锁保护
- [ ] Fix 2: 实现 `QuotesService.close()` 方法
- [ ] Fix 2: 在 `main.py` lifespan 中调用 `close()`
- [ ] Fix 3: 删除 `main.py` 中重复的 except 块
- [ ] 运行代码质量检查
- [ ] 运行并发测试
- [ ] 验证无资源泄漏

---

**修复优先级**: P0 - 必须在合并前完成  
**预计工作量**: 30-45 分钟  
**测试要求**: 必须通过并发测试

## Epic 1: 数据基础层

### Epic 目标

建立**稳定可替换**的数据获取层。akshare 不稳定是常态,架构必须假设它会故障。

### Stories

---

#### Story 1.1: DataSource 抽象基类

**技术实现:**

```python
# backend/src/cci_monitor/data/base.py
from abc import ABC, abstractmethod
from datetime import date
import pandas as pd

class DataSource(ABC):
    """数据源抽象基类."""
    
    name: str
    
    @abstractmethod
    async def fetch_index_daily(
        self, symbol: str, 
        start_date: date, 
        end_date: date | None = None
    ) -> pd.DataFrame:
        """
        获取指数日度行情.
        
        Returns:
            DataFrame with columns: 
                - date (pd.Timestamp)
                - open, high, low, close, volume (float)
                - change_pct (float, 百分比如 1.5 表示 1.5%)
        """
        ...
    
    @abstractmethod
    async def fetch_index_components(self, index_code: str) -> list[str]:
        """
        获取指数成分股代码列表.
        
        Args:
            index_code: '000300' / '000905' / '000852' 等
        
        Returns:
            股票代码列表,带市场后缀如 ['600519.SH', '000001.SZ']
        """
        ...
    
    @abstractmethod
    async def fetch_stock_daily(
        self, code: str, 
        start_date: date, 
        end_date: date | None = None
    ) -> pd.DataFrame:
        """获取单只股票日度数据,格式同 fetch_index_daily."""
        ...
    
    async def fetch_stocks_batch(
        self, codes: list[str],
        start_date: date,
        end_date: date | None = None,
        concurrency: int = 5,
    ) -> pd.DataFrame:
        """
        并发批量获取,返回宽表.
        
        Returns:
            DataFrame: index=date, columns=codes, values=change_pct
        """
        import asyncio
        semaphore = asyncio.Semaphore(concurrency)
        
        async def fetch_one(code: str):
            async with semaphore:
                try:
                    df = await self.fetch_stock_daily(code, start_date, end_date)
                    return code, df
                except Exception as e:
                    logger.warning(f"Failed to fetch {code}: {e}")
                    return code, pd.DataFrame()
        
        results = await asyncio.gather(*[fetch_one(c) for c in codes])
        # 合并为宽表
        series_dict = {}
        for code, df in results:
            if not df.empty:
                series_dict[code] = df.set_index("date")["change_pct"]
        return pd.DataFrame(series_dict)
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """健康检查."""
        ...
```

**验收标准:**
- [ ] 接口规范使用 async/await
- [ ] 批量方法默认实现并发调用
- [ ] 有完整的 docstring 包含返回格式

**预计工时:** 2 小时

---

#### Story 1.2: akshare 数据源实现

**技术实现:**

```python
# backend/src/cci_monitor/data/akshare_source.py
import akshare as ak
import asyncio
import pandas as pd
from datetime import date, datetime
from ..core.exceptions import DataSourceEmptyError, DataSourceTimeoutError, DataSourceError
from .base import DataSource
from ..core.logger import logger

class AkshareDataSource(DataSource):
    name = "akshare"
    
    async def _run_sync(self, func, *args, **kwargs):
        """在线程池中执行同步 akshare 调用."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                timeout=30,
            )
        except asyncio.TimeoutError:
            raise DataSourceTimeoutError(f"akshare timeout: {func.__name__}")
        except Exception as e:
            raise DataSourceError(f"akshare failed: {e}", exception=str(e))
    
    async def fetch_index_daily(self, symbol, start_date, end_date=None):
        end_date = end_date or date.today()
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        df = await self._run_sync(
            ak.stock_zh_index_daily_em,
            symbol=symbol,
            start_date=start_str,
            end_date=end_str,
        )
        
        if df.empty:
            raise DataSourceEmptyError(f"no data for {symbol}")
        
        # 标准化字段
        df = df.rename(columns=str.lower)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["change_pct"] = df["close"].pct_change() * 100
        
        return df[["date", "open", "high", "low", "close", "volume", "change_pct"]]
    
    async def fetch_index_components(self, index_code):
        df = await self._run_sync(ak.index_stock_cons_sina, symbol=index_code)
        if df.empty:
            raise DataSourceEmptyError(f"no components for {index_code}")
        
        codes = []
        for code in df["code"].tolist():
            suffix = ".SH" if code.startswith("6") else ".SZ"
            codes.append(f"{code}{suffix}")
        return codes
    
    async def fetch_stock_daily(self, code, start_date, end_date=None):
        end_date = end_date or date.today()
        pure_code = code.split(".")[0] if "." in code else code
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        df = await self._run_sync(
            ak.stock_zh_a_hist,
            symbol=pure_code,
            period="daily",
            start_date=start_str,
            end_date=end_str,
            adjust="qfq",
        )
        
        if df.empty:
            raise DataSourceEmptyError(f"no data for {code}")
        
        # 标准化字段(注意 akshare 中文列名)
        column_mapping = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "涨跌幅": "change_pct",
        }
        df = df.rename(columns=column_mapping)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        return df[["date", "open", "high", "low", "close", "volume", "change_pct"]]
    
    async def is_healthy(self):
        try:
            # 拉取一个小样本验证
            df = await self.fetch_index_daily(
                "sh000300",
                date.today() - pd.Timedelta(days=7),
                date.today(),
            )
            return not df.empty
        except Exception:
            return False
```

**验收标准:**
- [ ] 所有异常被包装为项目异常
- [ ] 使用 asyncio.wait_for 强制超时
- [ ] 批量接口(fetch_stocks_batch)使用信号量控制并发
- [ ] 有集成测试(需要网络)

**预计工时:** 6-8 小时

---

#### Story 1.3: 缓存层

**技术实现:**

```python
# backend/src/cci_monitor/data/cache.py
from pathlib import Path
import pandas as pd
import hashlib
import json
from datetime import datetime, date, timedelta

class Cache:
    """基于 parquet 文件的本地缓存."""
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _key(self, namespace: str, **params) -> str:
        """生成缓存键."""
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        hash_str = hashlib.md5(sorted_params.encode()).hexdigest()[:8]
        return f"{namespace}_{hash_str}"
    
    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.parquet"
    
    def _meta_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.meta.json"
    
    def get(self, namespace: str, ttl_override: timedelta | None = None, **params) -> pd.DataFrame | None:
        key = self._key(namespace, **params)
        path = self._path(key)
        meta_path = self._meta_path(key)
        
        if not path.exists() or not meta_path.exists():
            return None
        
        # 检查 TTL
        meta = json.loads(meta_path.read_text())
        cached_at = datetime.fromisoformat(meta["cached_at"])
        effective_ttl = ttl_override or self.ttl
        if datetime.now() - cached_at > effective_ttl:
            return None
        
        try:
            return pd.read_parquet(path)
        except Exception:
            return None
    
    def set(self, namespace: str, df: pd.DataFrame, **params):
        key = self._key(namespace, **params)
        path = self._path(key)
        meta_path = self._meta_path(key)
        
        df.to_parquet(path, index=False)
        meta_path.write_text(json.dumps({
            "cached_at": datetime.now().isoformat(),
            "params": params,
            "rows": len(df),
        }, default=str))
    
    def clear(self, namespace: str | None = None):
        pattern = f"{namespace}_*" if namespace else "*"
        for f in self.cache_dir.glob(pattern):
            f.unlink()
```

**缓存策略实现:**

```python
# CachedDataSource 装饰
class CachedDataSource(DataSource):
    """给任何 DataSource 加上缓存."""
    
    def __init__(self, inner: DataSource, cache: Cache):
        self.inner = inner
        self.cache = cache
        self.name = f"cached({inner.name})"
    
    async def fetch_index_daily(self, symbol, start_date, end_date=None):
        end_date = end_date or date.today()
        
        # 历史数据永久缓存,近期数据短期缓存
        is_recent = (date.today() - end_date).days < 3
        ttl = timedelta(hours=1) if is_recent else timedelta(days=30)
        
        cached = self.cache.get(
            "index_daily",
            ttl_override=ttl,
            symbol=symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )
        if cached is not None:
            logger.debug(f"cache hit: index_daily {symbol}")
            return cached
        
        df = await self.inner.fetch_index_daily(symbol, start_date, end_date)
        self.cache.set(
            "index_daily", df,
            symbol=symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )
        return df
    
    # 其他方法类似...
```

**验收标准:**
- [ ] 缓存命中 < 100ms
- [ ] 历史数据永久缓存,近期数据 TTL 1 小时
- [ ] 文件损坏时自动失效
- [ ] 提供 `scripts/clear_cache.py`

**预计工时:** 4 小时

---

#### Story 1.4: 弹性层(降级/重试/断路器)

**As a** 运维者
**I want** 数据源故障时系统仍能运行
**So that** akshare 挂了不影响整体可用性

**技术实现:**

```python
# backend/src/cci_monitor/data/resilience.py
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..core.exceptions import DataSourceTimeoutError, DataSourceRateLimitError
from ..core.logger import logger

def with_retry(func):
    """重试装饰器: 超时或限流自动重试."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((DataSourceTimeoutError, DataSourceRateLimitError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying {func.__name__} (attempt {retry_state.attempt_number})"
        ),
        reraise=True,
    )(func)

class CircuitBreaker:
    """简单断路器,防止雪崩."""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = None
        self.state: Literal["closed", "open", "half_open"] = "closed"
    
    def record_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error("Circuit breaker opened")
    
    def can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half_open"
                return True
            return False
        return True  # half_open: 允许试探
```

**验收标准:**
- [ ] 超时错误自动重试(指数退避)
- [ ] 连续 5 次失败触发断路器
- [ ] 断路器 60 秒后进入 half_open 尝试恢复

**预计工时:** 3 小时

---


import asyncio
import logging
import hashlib
import os
import random
import signal
from datetime import datetime, time
from collections import deque
from typing import List, Dict, Tuple, Optional, Any
import aiohttp
import asynch
import pytz
import yaml
import redis.asyncio as aioredis
from gsd_shared.stock_universe import StockUniverseService
from gsd_shared.tick import clean_stock_code
from gsd_shared.validators import is_valid_index

# 导入项目依赖
from src.core.scheduling.calendar_service import CalendarService
from src.core.collector.components.writer import ClickHouseWriter

from src.core.collector.components.snapshot_worker import SnapshotWorker
from src.core.collector.components.tick_worker import TickWorker

logger = logging.getLogger("IntradayTickCollector")
CST = pytz.timezone('Asia/Shanghai')

# 常量定义 (可通过环境变量覆盖)
FINGERPRINT_CACHE_SIZE = int(os.getenv("FINGERPRINT_CACHE_SIZE", "60000"))
FLUSH_THRESHOLD = int(os.getenv("FLUSH_THRESHOLD", "3000"))
FLUSH_INTERVAL_SECONDS = float(os.getenv("FLUSH_INTERVAL_SECONDS", "5"))
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "4.0"))
POLL_OFFSET = int(os.getenv("POLL_OFFSET", "200"))  # 获取深度对齐文档建议
DEFAULT_CONCURRENCY = int(os.getenv("CONCURRENCY", "64"))

# 分片配置 (分布式模式)
SHARD_INDEX = int(os.getenv("SHARD_INDEX", "0"))
SHARD_TOTAL = int(os.getenv("SHARD_TOTAL", "1"))  # 1=单机模式, >1=分布式模式
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis123")
REDIS_SHARD_KEY_PREFIX = "metadata:stock_codes:shard"
REDIS_CONNECT_TIMEOUT = 5  # Redis 连接超时 (秒)
REDIS_SOCKET_TIMEOUT = 10  # Redis 读写超时 (秒)
REDIS_MAX_CONNECTIONS = 100 # Redis 连接池最大连接数

# 快照采集配置
SNAPSHOT_INTERVAL_SECONDS = 3.0  # 快照采集间隔
SNAPSHOT_BATCH_SIZE = int(os.getenv("SNAPSHOT_BATCH_SIZE", "50"))  # 快照API单批大小(调小以增强稳定性)

class CircuitBreaker:
    """简单的熔断器实现，对齐文档质量标准"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN

    def is_available(self) -> bool:
        if self.state == "OPEN":
            if asyncio.get_running_loop().time() - self.last_failure_time > self.recovery_timeout:
                self.state = "CLOSED"
                self.failure_count = 0
                return True
            return False
        return True

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = asyncio.get_running_loop().time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logging.getLogger("CircuitBreaker").error(f"🚨 Circuit Breaker OPEN! Cooling down for {self.recovery_timeout}s")

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

class IntradayTickCollector:
    """
    盘中分笔采集器 (支持单机/分布式模式)
    
    职责:
    - 定时轮询股票池
    - 增量获取分笔数据
    - 内存中维护指纹缓存去重
    - 批量异步写入 ClickHouse
    
    模式:
    - SHARD_TOTAL=1: 单机模式，从本地 YAML 文件加载股票池 (HS300池)
    - SHARD_TOTAL>1: 分布式模式，从 Redis 读取分片股票池
    """

    def __init__(self, stock_pool_path: Optional[str] = None):
        self.mootdx_api_url = os.getenv("MOOTDX_API_URL", "http://127.0.0.1:8003")
        self.stock_pool_path = stock_pool_path or os.getenv("STOCK_POOL_PATH", "/app/config/hs300_stocks.yaml")
        
        # 内部状态
        self.stock_pool: List[str] = []
        self.fingerprints: Dict[str, deque] = {}  # code -> deque([fp1, fp2, ...])
        self.write_buffer: List[Tuple] = []
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        
        # 并发安全锁 (CRITICAL FIX)
        self._buffer_lock = asyncio.Lock()
        
        # 组件
        self.writer: Optional[ClickHouseWriter] = None

        self.snapshot_worker: Optional[SnapshotWorker] = None
        self.tick_worker: Optional[TickWorker] = None
        
        # 交易日历服务
        self.calendar = CalendarService()
        
        # 资源池
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.clickhouse_pool: Any = None
        self.redis_client: Optional[aioredis.Redis] = None
        
        # 并发控制信号量
        # 使用环境变量 CONCURRENCY 配置 (默认 16)
        concurrency = DEFAULT_CONCURRENCY
        self.snapshot_sem = asyncio.Semaphore(concurrency) 
        self.tick_sem = asyncio.Semaphore(concurrency)
        
        # 分片配置
        self.shard_index = SHARD_INDEX
        self.shard_total = SHARD_TOTAL

        # 熔断器 (对齐 03_CODE_QUALITY.md)
        self.api_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)


        
        # Stock Universe Service
        self.stock_universe = None
                
    async def initialize(self):
        """初始化资源和股票池"""
        logger.info("🚀 Initializing IntradayTickCollector...")
        
        # 0. 初始化 Redis (用于 StockUniverse)
        if self.redis_client is None:
            self.redis_client = aioredis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True,
                max_connections=REDIS_MAX_CONNECTIONS,
                socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
                socket_timeout=REDIS_SOCKET_TIMEOUT
            )
            try:
                await self.redis_client.ping()
                logger.info(f"✅ Redis connected ({REDIS_HOST}:{REDIS_PORT})")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}. StockUniverse will attempt fallbacks.")
                # We do NOT unset self.redis_client, allowing StockUniverse to try usage and handle errors internally
                # or we could set it to None if we want to force fallback immediately.
                # StockUniverse handles redis exceptions, so passing the client is fine.

        # 1. 初始化 StockUniverseService
        self.stock_universe = StockUniverseService(
            redis_client=self.redis_client
        )
        
        # 2. 加载股票池
        await self._load_stock_pool()
        

        
        # 3. 初始化 ClickHouse 
        if self.clickhouse_pool is None:
            self.clickhouse_pool = await asynch.create_pool(
                host=os.getenv("CLICKHOUSE_HOST", "127.0.0.1"),
                port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
                database=os.getenv("CLICKHOUSE_DB", "stock_data"),
                user=os.getenv("CLICKHOUSE_USER", "default"),
                password=os.getenv("CLICKHOUSE_PASSWORD", ""),
                minsize=1,
                maxsize=20
            )
            logger.info("✅ ClickHouse pool initialized")
            
        # 初始化 Writer
        if self.writer is None:
            # Default to DISTRIBUTED table for cluster-wide visibility
            table_name = os.getenv("CLICKHOUSE_TICK_TABLE", "tick_data_intraday")
            self.writer = ClickHouseWriter(self.clickhouse_pool, table_name=table_name)

        # 4. 初始化 HTTP session (增加连接限制)
        if self.http_session is None:
            connector = aiohttp.TCPConnector(limit=256, keepalive_timeout=60)
            self.http_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=45)
            )
            logger.info(f"✅ HTTP session initialized (limit=256, mootdx-api: {self.mootdx_api_url})")

        # 4. 初始化 Workers
        if self.stock_pool:
            # --- 优化: 过滤掉指数，因为指数没有分笔明细，且可能导致快照 API 返回空结果 ---
            tick_pool = [c for c in self.stock_pool if not is_valid_index(clean_stock_code(c))]
            filtered_count = len(self.stock_pool) - len(tick_pool)
            if filtered_count > 0:
                logger.info(f"⚙️ Filtered {filtered_count} indices from stock pool.")

            # --- 优化: 随机打散代码池，混合沪深标的，防止同质化批次触发 API 拒绝 ---
            random.sample(tick_pool, len(tick_pool)) # 使用 sample 不改变原对象或直接 shuffle
            random.shuffle(tick_pool)
            logger.info(f"🎲 Stock pool shuffled (mixing SH/SZ batches)")

            # 初始化 SnapshotWorker
            if self.snapshot_worker is None:
                self.snapshot_worker = SnapshotWorker(
                    http_session=self.http_session,
                    writer=self.writer,
                    stock_pool=tick_pool, # 使用过滤后的池
                    semaphore=self.snapshot_sem,
                    mootdx_api_url=self.mootdx_api_url,
                    batch_size=SNAPSHOT_BATCH_SIZE,
                    interval=SNAPSHOT_INTERVAL_SECONDS,
                    circuit_breaker=self.api_circuit_breaker,
                    max_retries=3 # 确保传递重试参数 (默认 3)
                )

            # 初始化 TickWorker
            if self.tick_worker is None:
                logger.info(f"⚙️ TickWorker scheduled for {len(tick_pool)} stocks")
                self.tick_worker = TickWorker(
                    http_session=self.http_session,
                    writer=self.writer,
                    stock_pool=tick_pool,
                    semaphore=self.tick_sem,
                    mootdx_api_url=self.mootdx_api_url,
                    redis_client=self.redis_client,
                    circuit_breaker=self.api_circuit_breaker
                )

    async def _load_stock_pool(self):
        """
        加载股票池 (委托给 StockUniverseService)
        - SHARD_TOTAL=1: 加载全量 A 股
        - SHARD_TOTAL>1: 加载对应分片
        """
        try:
            # 1. 同时合并 A 股全域与 YAML 核心池 (确保 ETF 被包含)
            all_universe_stocks = await self.stock_universe.get_all_a_stocks()
            
            yaml_stocks = []
            if os.path.exists(self.stock_pool_path):
                with open(self.stock_pool_path, 'r') as f:
                    config = yaml.safe_load(f)
                    yaml_stocks = config.get('stocks', [])
                    if yaml_stocks:
                        logger.info(f"✅ Loaded {len(yaml_stocks)} core stocks from {self.stock_pool_path}")

            # 合并并去重
            combined_raw = sorted(list(set(all_universe_stocks + yaml_stocks)))
            
            # 2. 根据模式筛选当前节点负责的标的
            if self.shard_total > 1:
                logger.info(f"Using Distributed Mode: Sharding {len(combined_raw)} stocks -> Shard {self.shard_index}/{self.shard_total}")
                # 使用 StockUniverse 的稳定哈希分片算法
                raw_stocks = self.stock_universe._shard_filter(combined_raw, self.shard_index, self.shard_total)
            else:
                logger.info(f"Using Standalone Mode: Processing {len(combined_raw)} stocks")
                raw_stocks = combined_raw
            
            if not raw_stocks:
                logger.warning("⚠️ StockUniverse returned empty list!")
            
            # 格式化为 mootdx-api 需要的前缀格式 (sh/sz)
            self.stock_pool = []
            for code_in in raw_stocks:
                # 归一化为 TS 格式 (如 600519.SH)
                ts_code = clean_stock_code(code_in)
                if not ts_code or '.BJ' in ts_code:
                    continue
                
                pure_code, market = ts_code.split('.')
                
                # 彻底丢弃北交所及新三板股票
                # 因为底层 PyTDX 不支持 8 / 4 / 9 开头的 A 股行情，强行请求会导致 Socket 线程堵塞 15s 从而拖垮整个服务。
                if pure_code.startswith(('8', '4', '9')):
                    continue
                
                # 统一使用归一化后的市场标识 (sh/sz) 作为前缀
                self.stock_pool.append(f"{market.lower()}{pure_code}")
            
            # 初始化指纹
            for code in self.stock_pool:
                if code not in self.fingerprints:
                    self.fingerprints[code] = deque(maxlen=FINGERPRINT_CACHE_SIZE)
                    
            logger.info(f"✅ Stock Pool Ready: {len(self.stock_pool)} stocks")
            
        except Exception as e:
            logger.error(f"❌ Failed to load stock pool: {e}", exc_info=True)
            raise

    def _is_trading_time(self) -> bool:
        """检查是否在 A 股交易时间 (9:25-11:30, 13:00-15:00)"""
        now = datetime.now(CST)
        
        # 1. 检查是否为交易日 (CRITICAL FIX: 使用 CalendarService)
        if not self.calendar.is_trading_day(now.date()):
            return False
            
        # 2. 检查交易时段
        t = now.time()
        # 提前一分钟启动以捕获 9:25 集合竞价
        return (
            (time(9, 24) <= t <= time(11, 35)) or
            (time(12, 59) <= t <= time(15, 5))
        )

    def _gen_fingerprint(self, item: Dict[str, Any]) -> str:
        """生成分笔数据的唯一指纹"""
        # 字段选取：时间、价格、成交量、买卖方向
        # 注意：mootdx-api 返回的字段通常是 'time', 'price', 'volume', 'type'
        t = item.get('time', '')
        p = item.get('price', 0)
        v = item.get('volume', item.get('vol', 0))
        d = item.get('type', item.get('buyorsell', 'NEUTRAL'))
        num = item.get('num', item.get('no', item.get('index', 0)))
        
        s = f"{t}|{p}|{v}|{d}|{num}"
        return hashlib.md5(s.encode()).hexdigest()

    async def _fetch_stock_ticks(self, code: str) -> List[Dict[str, Any]]:
        """从 mootdx-api 获取实时分笔"""
        url = f"{self.mootdx_api_url}/api/v1/tick/{code}"
        params = {"start": 0, "offset": POLL_OFFSET}  # 获取最新 N 条
        
        if self.http_session is None:
            return []
            
        try:
            async with self.http_session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"⚠️ Failed to fetch {code}: HTTP {resp.status}")
        except Exception as e:
            logger.warning(f"⚠️ Error fetching {code}: {e}")
        return []

    async def poll_stock(self, code: str):
        """采集单只股票并处理"""
        async with self.tick_sem:
            ticks = await self._fetch_stock_ticks(code)
            if not ticks:
                return

            today = datetime.now(CST).date()
            new_rows = []
            
            # API 返回通常是最新在前，我们按时间升序处理或直接处理（ReplacingMergeTree会处理冲突）
            # 这里指纹去重
            for item in ticks:
                fp = self._gen_fingerprint(item)
                if fp not in self.fingerprints[code]:
                    # 映射字段到 ClickHouse 
                    time_str = str(item.get('time', ''))
                    if len(time_str) == 5:
                        time_str += ":00"
                    
                    price = float(item.get('price', 0))
                    volume = int(item.get('volume', item.get('vol', 0)))
                    direction_str = item.get('type', 'NEUTRAL')
                    direction = self._map_direction(direction_str)
                    num = int(item.get('num', item.get('no', item.get('index', 0))))
                    
                    # (stock_code, trade_date, tick_time, price, volume, amount, direction, num)
                    new_rows.append((
                        clean_stock_code(code), # 存储 TS 格式代码 (如 600519.SH)
                        today,
                        time_str,
                        price,
                        volume,
                        price * volume,
                        direction,
                        num
                    ))
                    self.fingerprints[code].append(fp)
            
            if new_rows and self.writer:
                await self.writer.add_ticks(new_rows)
                # logger.debug(f"✅ {code}: Added {len(new_rows)} new ticks")

    def _map_direction(self, d: str) -> int:
        """映射买卖方向"""
        mapping = {"BUY": 0, "SELL": 1, "NEUTRAL": 2}
        return mapping.get(d, 2)

    async def flush_to_clickhouse(self):
        """批量将数据写入 ClickHouse (委托给 Writer)"""
        if self.writer:
            await self.writer.flush()

    async def _wait_for_trading(self):
        """非交易时间休眠"""
        logger.info("⏸️ Waiting for trading session...")
        while not self._is_trading_time() and not self._shutdown_event.is_set():
            await asyncio.sleep(60)

    async def run(self):
        """主循环 - 双协程并行模式"""
        self.is_running = True
        
        # CRITICAL FIX: 使用 try...finally 确保资源释放
        try:
            await self.initialize()
            
            # 创建两个并行任务
            snapshot_task = asyncio.create_task(self._snapshot_loop())
            tick_task = asyncio.create_task(self._tick_loop())
            
            # 等待两个任务（任一停止则全部停止）
            await asyncio.gather(snapshot_task, tick_task, return_exceptions=True)
            
        finally:
            # 确保资源释放
            await self.stop()
    
    async def _snapshot_loop(self):
        """快照采集循环 (委托给 Worker)"""
        if self.snapshot_worker:
            await self.snapshot_worker.run(self._shutdown_event, self._is_trading_time)
        else:
            logger.warning("⚠️ SnapshotWorker not initialized, skipping snapshot loop")
    
    async def _tick_loop(self):
        """分笔采集循环 (委托给 Worker)"""
        if self.tick_worker:
            await self.tick_worker.run(self._shutdown_event, self._is_trading_time)
        else:
            logger.warning("⚠️ TickWorker not initialized, skipping tick loop")
    


    async def stop(self):
        """发送停止信号 (不释放资源)"""
        logger.info("🛑 Signal received: Stopping IntradayTickCollector...")
        self._shutdown_event.set()

    async def close(self):
        """释放资源 (应当在 run() 结束后调用)"""
        from asynch.pool import Pool as AsynchPool
        
        logger.info("🧹 Cleaning up resources...")
        
        # 1. 先关闭 Writer (会触发最后一次 Flush)
        if self.writer:
            try:
                await self.writer.close()
            except Exception as e:
                logger.error(f"❌ Error closing writer: {e}")
            
        # 2. 释放资源
        if self.http_session:
            await self.http_session.close()
            
        if self.clickhouse_pool:
            # 检查 pool 是否已被关闭
            if isinstance(self.clickhouse_pool, AsynchPool) and not self.clickhouse_pool._closed:
                self.clickhouse_pool.close()
                await self.clickhouse_pool.wait_closed()
            elif hasattr(self.clickhouse_pool, 'close'):
                 self.clickhouse_pool.close()
                 try:
                     await self.clickhouse_pool.wait_closed()
                 except Exception:
                     pass

        if self.redis_client:
            await self.redis_client.close()
            
        logger.info("✅ IntradayTickCollector closed")

def setup_signals(collector: IntradayTickCollector):
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(collector.stop()))

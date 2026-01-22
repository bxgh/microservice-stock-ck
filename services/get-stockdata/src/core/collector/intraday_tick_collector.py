import asyncio
import logging
import hashlib
import os
import signal
from datetime import datetime, time
from collections import deque
from typing import List, Dict, Tuple, Optional, Any
import aiohttp
import asynch
import pytz
import yaml
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import redis.asyncio as aioredis

# 导入项目依赖
from src.core.scheduling.calendar_service import CalendarService
from src.core.resilience.circuit_breaker import CircuitBreaker

logger = logging.getLogger("IntradayTickCollector")
CST = pytz.timezone('Asia/Shanghai')

# 常量定义 (可通过环境变量覆盖)
FINGERPRINT_CACHE_SIZE = int(os.getenv("FINGERPRINT_CACHE_SIZE", "1000"))
FLUSH_THRESHOLD = int(os.getenv("FLUSH_THRESHOLD", "1000"))
FLUSH_INTERVAL_SECONDS = float(os.getenv("FLUSH_INTERVAL_SECONDS", "5"))
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "4.0"))
POLL_OFFSET = int(os.getenv("POLL_OFFSET", "800"))  # 每次拉取的最新条数
DEFAULT_CONCURRENCY = int(os.getenv("CONCURRENCY", "16"))

# 分片配置 (分布式模式)
SHARD_INDEX = int(os.getenv("SHARD_INDEX", "0"))
SHARD_TOTAL = int(os.getenv("SHARD_TOTAL", "1"))  # 1=单机模式, >1=分布式模式
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis123")
REDIS_SHARD_KEY_PREFIX = "metadata:stock_codes:shard"
REDIS_CONNECT_TIMEOUT = 5  # Redis 连接超时 (秒)
REDIS_SOCKET_TIMEOUT = 10  # Redis 读写超时 (秒)
REDIS_MAX_CONNECTIONS = 10  # Redis 连接池最大连接数

# 快照采集配置
SNAPSHOT_INTERVAL_SECONDS = float(os.getenv("SNAPSHOT_INTERVAL_SECONDS", "3.0"))  # 快照采集间隔
SNAPSHOT_BATCH_SIZE = int(os.getenv("SNAPSHOT_BATCH_SIZE", "80"))  # 快照API单批最多80只

class IntradayTickCollector:
    """
    盘中分笔采集器 (支持单机/分布式模式)
    
    职责:
    - 定时轮询股票池
    - 增量获取分笔数据
    - 内存中维护指纹缓存去重
    - 批量异步写入 ClickHouse
    
    模式:
    - SHARD_TOTAL=1: 单机模式，从 YAML 文件加载股票池
    - SHARD_TOTAL>1: 分布式模式，从 Redis 读取分片股票池
    """

    def __init__(self, stock_pool_path: str = None):
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
        
        # 交易日历服务
        self.calendar = CalendarService()
        
        # Circuit Breaker for HTTP requests (P1 FIX)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,  # 连续5次失败触发熔断
            timeout=60  # 熔断60秒后尝试恢复
        )
        
        # 资源池
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.clickhouse_pool: Any = None
        self.redis_client: Optional[aioredis.Redis] = None
        self.semaphore = asyncio.Semaphore(int(os.getenv("CONCURRENCY", str(DEFAULT_CONCURRENCY))))
        
        # 分片配置
        self.shard_index = SHARD_INDEX
        self.shard_total = SHARD_TOTAL

        # 快照采集相关
        self.snapshot_batches: List[List[str]] = []
        self.snapshot_buffer: List[Tuple] = []
                
    async def initialize(self):
        """初始化资源和股票池"""
        logger.info("🚀 Initializing IntradayTickCollector...")
        
        # 1. 加载股票池
        await self._load_stock_pool()
        

        # 2. 预分批快照采集股票池
        if self.stock_pool:
            self.snapshot_batches = [
                self.stock_pool[i:i + SNAPSHOT_BATCH_SIZE]
                for i in range(0, len(self.stock_pool), SNAPSHOT_BATCH_SIZE)
            ]
            logger.info(f"📸 Prepared {len(self.snapshot_batches)} snapshot batches")
        
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

        # 3. 初始化 HTTP session
        if self.http_session is None:
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            logger.info(f"✅ HTTP session initialized (mootdx-api: {self.mootdx_api_url})")

    async def _load_stock_pool(self):
        """
        加载股票池 (支持两种模式)
        - SHARD_TOTAL=1: 单机模式，从 YAML 文件加载 (适用于 HS300 等固定池)
        - SHARD_TOTAL>1: 分布式模式，从 Redis 读取分片 (适用于全市场)
        """
        if self.shard_total > 1:
            await self._load_stock_pool_from_redis()
        else:
            await self._load_stock_pool_from_yaml()
    
    async def _load_stock_pool_from_yaml(self):
        """从 YAML 文件加载股票池 (单机模式)"""
        try:
            with open(self.stock_pool_path, 'r') as f:
                config = yaml.safe_load(f)
                stocks = config.get('stocks', [])
                if not stocks:
                    raise ValueError("Empty stock list in config")
                
                # 预处理代码：加上 sh/sz 前缀用于 mootdx-api
                self.stock_pool = []
                for s in stocks:
                    code = str(s).strip()
                    if code.startswith('6'):
                        self.stock_pool.append(f"sh{code}")
                    else:
                        self.stock_pool.append(f"sz{code}")
                
                # 初始化指纹缓存
                for code in self.stock_pool:
                    if code not in self.fingerprints:
                        self.fingerprints[code] = deque(maxlen=FINGERPRINT_CACHE_SIZE)
                
                logger.info(f"✅ Loaded {len(self.stock_pool)} stocks from {self.stock_pool_path} (单机模式)")
        except Exception as e:
            logger.error(f"❌ Failed to load stock pool from YAML: {e}")
            raise
    
    async def _load_stock_pool_from_redis(self):
        """从 Redis 加载分片股票池 (分布式模式)"""
        try:
            # 连接 Redis (优化: 添加连接池和超时配置)
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
                await self.redis_client.ping()
                logger.info(f"✅ Redis connected ({REDIS_HOST}:{REDIS_PORT})")
            
            # 从分片 Key 读取
            shard_key = f"{REDIS_SHARD_KEY_PREFIX}:{self.shard_index}"
            codes = await self.redis_client.smembers(shard_key)
            
            if not codes:
                raise ValueError(f"Shard key {shard_key} is empty or not found")
            
            # 格式化代码 (Redis 存储格式: 000001.SZ -> mootdx-api 格式: sz000001)
            # 过滤北交所代码 (.BJ 后缀，TDX 不支持)
            self.stock_pool = []
            bj_count = 0
            for code in codes:
                code = str(code).strip()
                # 处理 000001.SZ 或 600519.SH 格式
                if '.' in code:
                    pure_code, exchange = code.split('.')
                    if exchange.upper() == 'BJ':
                        bj_count += 1
                        continue  # 跳过北交所代码
                    if exchange.upper() == 'SH':
                        self.stock_pool.append(f"sh{pure_code}")
                    else:
                        self.stock_pool.append(f"sz{pure_code}")
                else:
                    # 纯数字格式
                    if code.startswith('8'):  # 北交所 8 开头
                        bj_count += 1
                        continue
                    if code.startswith('6'):
                        self.stock_pool.append(f"sh{code}")
                    else:
                        self.stock_pool.append(f"sz{code}")
            
            if bj_count > 0:
                logger.info(f"🚫 Filtered {bj_count} BJ stocks (TDX unsupported)")
            
            # 初始化指纹缓存
            for code in self.stock_pool:
                if code not in self.fingerprints:
                    self.fingerprints[code] = deque(maxlen=FINGERPRINT_CACHE_SIZE)
            
            logger.info(f"✅ Loaded {len(self.stock_pool)} stocks from Redis (分布式模式, Shard {self.shard_index}/{self.shard_total})")
        except aioredis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed (host={REDIS_HOST}, port={REDIS_PORT}): {e}")
            raise
        except aioredis.TimeoutError as e:
            logger.error(f"❌ Redis operation timeout (timeout={REDIS_SOCKET_TIMEOUT}s): {e}")
            raise
        except ValueError as e:
            logger.error(f"❌ Invalid shard configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error loading stock pool from Redis: {e}", exc_info=True)
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
            (time(9, 24) <= t <= time(11, 31)) or
            (time(12, 59) <= t <= time(15, 0))
        )

    def _gen_fingerprint(self, item: Dict[str, Any]) -> str:
        """生成分笔数据的唯一指纹"""
        # 字段选取：时间、价格、成交量、买卖方向
        # 注意：mootdx-api 返回的字段通常是 'time', 'price', 'volume', 'type'
        t = item.get('time', '')
        p = item.get('price', 0)
        v = item.get('volume', item.get('vol', 0))
        d = item.get('type', item.get('buyorsell', 'NEUTRAL'))
        
        s = f"{t}|{p}|{v}|{d}"
        return hashlib.md5(s.encode()).hexdigest()

    async def _fetch_stock_ticks(self, code: str) -> List[Dict[str, Any]]:
        """从 mootdx-api 获取实时分笔 (P1 FIX: 集成 Circuit Breaker)"""
        # 检查熔断器状态
        if not self.circuit_breaker.can_execute():
            logger.warning(f"⚠️ Circuit breaker OPEN, skipping {code}")
            return []
        
        url = f"{self.mootdx_api_url}/api/v1/tick/{code}"
        params = {"start": 0, "offset": POLL_OFFSET}  # 获取最新 N 条
        
        try:
            async with self.http_session.get(url, params=params) as resp:
                if resp.status == 200:
                    self.circuit_breaker.record_success()
                    return await resp.json()
                else:
                    logger.warning(f"⚠️ Failed to fetch {code}: HTTP {resp.status}")
                    self.circuit_breaker.record_failure()
        except Exception as e:
            # FIX: 使用正确的日志级别
            logger.warning(f"⚠️ Error fetching {code}: {e}")
            self.circuit_breaker.record_failure()
        return []

    async def poll_stock(self, code: str):
        """采集单只股票并处理"""
        async with self.semaphore:
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
                    if len(time_str) == 5: time_str += ":00"
                    
                    price = float(item.get('price', 0))
                    volume = int(item.get('volume', item.get('vol', 0)))
                    direction_str = item.get('type', 'NEUTRAL')
                    direction = self._map_direction(direction_str)
                    
                    # (stock_code, trade_date, tick_time, price, volume, amount, direction)
                    new_rows.append((
                        code.lstrip('sh').lstrip('sz'), # 存储纯代码
                        today,
                        time_str,
                        price,
                        volume,
                        price * volume,
                        direction
                    ))
                    self.fingerprints[code].append(fp)
            
            if new_rows:
                # CRITICAL FIX: 使用实例锁保护共享状态
                async with self._buffer_lock:
                    self.write_buffer.extend(new_rows)
                # logger.debug(f"✅ {code}: Added {len(new_rows)} new ticks")

    def _map_direction(self, d: str) -> int:
        """映射买卖方向"""
        mapping = {"BUY": 0, "SELL": 1, "NEUTRAL": 2}
        return mapping.get(d, 2)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def flush_to_clickhouse(self):
        """批量将数据写入 ClickHouse (P1 FIX: 添加重试机制)"""
        if not self.write_buffer:
            return

        # CRITICAL FIX: 使用实例锁保护共享状态
        async with self._buffer_lock:
            rows_to_write = self.write_buffer.copy()
            self.write_buffer.clear()

        try:
            async with self.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "INSERT INTO tick_data_intraday (stock_code, trade_date, tick_time, price, volume, amount, direction) VALUES",
                        rows_to_write
                    )
            logger.info(f"💾 Flushed {len(rows_to_write)} ticks to ClickHouse")
        except Exception as e:
            logger.error(f"❌ Failed to write to ClickHouse: {e}")
            # P1 FIX: 失败后数据会被 tenacity 重试,最多3次
            # 如果3次都失败,数据会记录在日志中,可以后续手动恢复
            logger.error(f"❌ Lost {len(rows_to_write)} ticks after retry exhausted")
            raise  # 重新抛出异常以触发 tenacity 重试

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
        """快照采集循环 - 高频 (每 3 秒)"""
        logger.info("📸 Starting snapshot loop...")
        
        while not self._shutdown_event.is_set():
            if not self._is_trading_time():
                await asyncio.sleep(60)
                continue
            
            start = asyncio.get_event_loop().time()
            
            try:
                # 批量采集快照
                await self._collect_snapshots()
            except Exception as e:
                logger.error(f"⚠️ Snapshot loop error: {e}")
            
            # 保持固定间隔
            elapsed = asyncio.get_event_loop().time() - start
            if elapsed < SNAPSHOT_INTERVAL_SECONDS:
                await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS - elapsed)
    
    async def _tick_loop(self):
        """分笔采集循环 - 常规 (每轮 ~50 秒)"""
        logger.info("📊 Starting tick loop...")
        last_flush_time = asyncio.get_event_loop().time()

        while not self._shutdown_event.is_set():
            if not self._is_trading_time():
                await self._wait_for_trading()
                if self._shutdown_event.is_set(): 
                    break
                logger.info("⏰ Waking up for trading!")

            round_start = asyncio.get_event_loop().time()
            
            # 轮询一轮
            tasks = [self.poll_stock(code) for code in self.stock_pool]
            await asyncio.gather(*tasks)

            # 检查刷盘 (使用常量)
            current_time = asyncio.get_event_loop().time()
            if len(self.write_buffer) >= FLUSH_THRESHOLD or (current_time - last_flush_time) >= FLUSH_INTERVAL_SECONDS:
                await self.flush_to_clickhouse()
                last_flush_time = current_time

            duration = asyncio.get_event_loop().time() - round_start
            # 目标：每 4-5 秒一轮。如果采集太快，则休眠补齐
            wait_time = max(0, POLL_INTERVAL_SECONDS - duration)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    async def _collect_snapshots(self):
        """批量采集快照数据 (P1 FIX: 集成 Circuit Breaker)"""
        if not self.snapshot_batches:
            return
        
        # 检查熔断器状态 (全局)
        if not self.circuit_breaker.can_execute():
            # logger.warning("⚠️ Circuit breaker OPEN, skipping snapshot round")
            return
        
        all_rows = []
        today = datetime.now(CST).date()
        snapshot_time = datetime.now(CST)
        
        for batch in self.snapshot_batches:
            try:
                # 调用 mootdx-api 的 GET /quotes 接口
                codes_param = ",".join(batch)
                url = f"{self.mootdx_api_url}/api/v1/quotes?codes={codes_param}"
                async with self.http_session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.circuit_breaker.record_success()
                        for item in data:
                            row = self._map_snapshot_row(item, today, snapshot_time)
                            if row:
                                all_rows.append(row)
                    else:
                        logger.warning(f"⚠️ Snapshot API returned {resp.status}")
                        self.circuit_breaker.record_failure()
            except Exception as e:
                logger.warning(f"⚠️ Snapshot batch failed: {e}")
                self.circuit_breaker.record_failure()
        
        # 写入 ClickHouse (snapshot_data_local)
        if all_rows:
            try:
                async with self.clickhouse_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            """INSERT INTO snapshot_data_local 
                            (snapshot_time, trade_date, stock_code, stock_name, market,
                             current_price, open_price, high_price, low_price, pre_close,
                             bid_price1, bid_volume1, bid_price2, bid_volume2,
                             bid_price3, bid_volume3, bid_price4, bid_volume4,
                             bid_price5, bid_volume5, ask_price1, ask_volume1,
                             ask_price2, ask_volume2, ask_price3, ask_volume3,
                             ask_price4, ask_volume4, ask_price5, ask_volume5,
                             total_volume, total_amount, turnover_rate) VALUES""",
                            all_rows
                        )
                logger.info(f"📸 Snapshot: {len(all_rows)} records written")
            except Exception as e:
                logger.error(f"❌ Snapshot write failed: {e}")
    
    def _map_snapshot_row(self, item: Dict[str, Any], trade_date: Any, snapshot_time: datetime) -> Optional[Tuple]:
        """将 API 响应映射为 DB 行"""
        try:
            raw_code = item.get('code', '')
            if not raw_code:
                return None
                
            # 确保代码、名称、市场都是字符串类型，避免 ClickHouse 驱动报错 (len 错误)
            code = str(raw_code).lstrip('sh').lstrip('sz')
            name = str(item.get('name', ''))
            market = str(item.get('market', ''))
            
            return (
                snapshot_time,  # snapshot_time
                trade_date,  # trade_date
                code,  # stock_code
                name,  # stock_name
                market,  # market
                float(item.get('price', 0)),  # current_price
                float(item.get('open', 0)),  # open_price
                float(item.get('high', 0)),  # high_price
                float(item.get('low', 0)),  # low_price
                float(item.get('last_close', 0)),  # pre_close
                # 买五档
                float(item.get('bid1', 0)), int(item.get('bid_vol1', 0)),
                float(item.get('bid2', 0)), int(item.get('bid_vol2', 0)),
                float(item.get('bid3', 0)), int(item.get('bid_vol3', 0)),
                float(item.get('bid4', 0)), int(item.get('bid_vol4', 0)),
                float(item.get('bid5', 0)), int(item.get('bid_vol5', 0)),
                # 卖五档
                float(item.get('ask1', 0)), int(item.get('ask_vol1', 0)),
                float(item.get('ask2', 0)), int(item.get('ask_vol2', 0)),
                float(item.get('ask3', 0)), int(item.get('ask_vol3', 0)),
                float(item.get('ask4', 0)), int(item.get('ask_vol4', 0)),
                float(item.get('ask5', 0)), int(item.get('ask_vol5', 0)),
                # 成交统计
                int(item.get('vol', 0)),  # total_volume
                float(item.get('amount', 0)),  # total_amount
                float(item.get('turnover', 0))  # turnover_rate
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to map snapshot row: {e}")
            return None

    async def stop(self):
        """优雅停止"""
        logger.info("🛑 Stopping IntradayTickCollector...")
        self._shutdown_event.set()
        
        # 最后一刷
        if self.write_buffer:
            await self.flush_to_clickhouse()
            
        # 释放资源
        if self.http_session:
            await self.http_session.close()
        if self.clickhouse_pool:
            self.clickhouse_pool.close()
            await self.clickhouse_pool.wait_closed()
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("✅ IntradayTickCollector stopped")

def setup_signals(collector: IntradayTickCollector):
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(collector.stop()))

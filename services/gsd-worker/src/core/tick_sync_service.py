
"""
分笔数据同步核心服务 (Refactored)

重构后：作为 Orchestrator 编排各子模块
职责：
1. 资源初始化与管理
2. 协调各个组件完成同步任务
"""

import asyncio
import aiohttp
import asynch
from asynch.pool import Pool as AsynchPool
import os
import logging
import pytz
from datetime import datetime
from typing import List, Dict, Any, Optional
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster, ClusterNode

# 子组件
from core.task_queue import TickTaskQueue
from gsd_shared.stock_universe import StockUniverseService
from gsd_shared.validation.tick_validator import TickValidator
from gsd_shared.tick import TickFetcher, TickWriter
from gsd_shared.tick.constants import TABLE_INTRADAY_LOCAL, TABLE_HISTORY_LOCAL
from gsd_shared.tick.utils import clean_stock_code
from core.sync_status import SyncStatusTracker
from config.settings import settings

logger = logging.getLogger(__name__)

# 上海时区
CST = pytz.timezone('Asia/Shanghai')

class TickSyncService:
    """分笔数据同步服务 (Orchestrator)"""
    
    DEFAULT_MIN_PACING_INTERVAL = 0.1
    
    def __init__(self):
        self._lock = asyncio.Lock()
        
        # Resources
        self.clickhouse_pool: Optional[AsynchPool] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # Config
        self.mootdx_api_url: str = os.getenv("MOOTDX_API_URL", "http://mootdx-api:8000")
        self.redis_mode_is_cluster: bool = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
        self.redis_nodes: str = os.getenv(
            "REDIS_NODES", 
            "192.168.151.41:6379,192.168.151.58:6379,192.168.151.111:6379"
        )
        self.redis_host: str = os.getenv("REDIS_HOST", "127.0.0.1")
        self.redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password: str = os.getenv("REDIS_PASSWORD", "redis123")
        
        # MySQL Config for StockUniverse
        self.mysql_config = {
            "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
            "port": int(os.getenv("MYSQL_PORT", "36301")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", "alwaysup@888"),
            "db": os.getenv("MYSQL_DB", "alwaysup"),
            "autocommit": True
        }
        
        # Components (Initialized in initialize())
        self.task_queue: Optional[TickTaskQueue] = None
        self.stock_universe: Optional[StockUniverseService] = None
        self.validator: Optional[TickValidator] = None
        self.fetcher: Optional[TickFetcher] = None
        self.writer: Optional[TickWriter] = None
        self.tracker: Optional[SyncStatusTracker] = None

    async def initialize(self) -> None:
        """初始化资源及组件"""
        async with self._lock:
            # 1. Initialize Resources
            if self.clickhouse_pool is None:
                self.clickhouse_pool = await asyncio.wait_for(
                    asynch.create_pool(
                        host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
                        port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
                        database="stock_data",
                        user=os.getenv("CLICKHOUSE_USER", "default"),
                        password=os.getenv("CLICKHOUSE_PASSWORD", ""),
                        minsize=5,
                        maxsize=int(os.getenv("CLICKHOUSE_POOL_SIZE", "60")),
                        connect_timeout=settings.db_connect_timeout,
                        send_receive_timeout=settings.db_io_timeout,
                        sync_request_timeout=settings.db_io_timeout
                    ),
                    timeout=settings.db_connect_timeout + settings.db_connect_timeout_buffer
                )
            
            if self.http_session is None:
                timeout = aiohttp.ClientTimeout(total=120)
                self.http_session = aiohttp.ClientSession(timeout=timeout)
            
            if self.redis_client is None:
                try:
                    if self.redis_mode_is_cluster:
                        nodes = [ClusterNode(host, int(port)) 
                               for host, port in (n.split(":") for n in self.redis_nodes.split(","))]
                        self.redis_client = RedisCluster(
                            startup_nodes=nodes,
                            decode_responses=True, 
                            socket_timeout=5,
                            cluster_error_retry_attempts=3,
                            password=self.redis_password
                        )
                    else:
                        self.redis_client = redis.Redis(
                            host=self.redis_host,
                            port=self.redis_port,
                            password=self.redis_password,
                            decode_responses=True,
                            socket_timeout=5
                        )
                    await self.redis_client.ping()
                except Exception as e:
                    logger.warning(f"⚠️ Redis 初始化失败: {e}")
                    self.redis_client = None

            # 2. Initialize Components
            self.task_queue = TickTaskQueue(self.redis_client)
            
            # ClickHouse client wrapper needed for StockUniverse (simple adapter)
            # Since asynch pool is used here, we pass the pool directly if StockUniverse supports it
            # Or we pass a wrapper. StockUniverse expects an object with execute/execute_async or client.execute
            # Here we pass a simple wrapper to adapt pool to client-like interface if needed, 
            # Or simplified: pass None for now given CH logic is mainly in PostMarketGate, 
            # BUT TickSync uses get_from_kline, so we need CH.
            
            # Init StockUniverse
            # Note: StockUniverseService supports mysql_config and redis, and ch_client
            # We don't have mysql config here (it uses ENV vars in Universe), so we rely on Redis.
            # For CH, we can wrap the pool.
            
            class CHPoolAdapter:
                def __init__(self, pool): self.pool = pool
                async def execute_async(self, query):
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(query)
                            return await cur.fetchall()

            self.stock_universe = StockUniverseService(
                redis_client=self.redis_client,
                mysql_config=self.mysql_config,
                clickhouse_client=CHPoolAdapter(self.clickhouse_pool)
            )
            self.validator = TickValidator(self.clickhouse_pool)
            self.fetcher = TickFetcher(self.http_session, self.mootdx_api_url, mode=TickFetcher.Mode.HISTORICAL)
            self.writer = TickWriter(self.clickhouse_pool)
            self.tracker = SyncStatusTracker(self.redis_client)
            
            logger.info("✓ TickSyncService Components Initialized")

    async def close(self) -> None:
        """关闭资源"""
        async with self._lock:
            if self.clickhouse_pool:
                self.clickhouse_pool.close()
                await self.clickhouse_pool.wait_closed()
                self.clickhouse_pool = None
            if self.http_session:
                await self.http_session.close()
                self.http_session = None
            if self.redis_client:
                await self.redis_client.aclose()
                self.redis_client = None
            logger.info("✓ Resources Closed")

    async def purge_tick_data(self, trade_date: str, stock_codes: Optional[List[str]] = None, force_all: bool = False) -> bool:
        """
        物理清理异常分笔数据
        :param stock_codes: 如果为 None，则尝试清理该日期全天数据 (受阈值限制)
        :param force_all: 是否强制执行全量清理 (跳过阈值检查)
        """
        if not self.clickhouse_pool:
            return False

        try:
            # 统一日期格式 YYYY-MM-DD
            trade_date_dt = trade_date.replace('-', '')
            formatted_date = f"{trade_date_dt[:4]}-{trade_date_dt[4:6]}-{trade_date_dt[6:8]}"
            
            # 动态选择目标表
            today_str = datetime.now(CST).strftime("%Y%m%d")
            target_table = TABLE_INTRADAY_LOCAL if trade_date_dt == today_str else TABLE_HISTORY_LOCAL
            
            # [Safety Valve V4.0] 风险控制：防止意外全表删除
            if stock_codes is None:
                if not force_all:
                    logger.error(f"❌ [Safety Valve] 拒绝全天全量清理 ({formatted_date})，必须显式指定 force_all=True")
                    return False
                
                # 全天全量清理模式 (单次 Mutation，最高效)
                sql = f"ALTER TABLE stock_data.{target_table} ON CLUSTER stock_cluster DELETE WHERE trade_date = '{formatted_date}'"
                logger.warning(f"🚨 [CRITICAL] 正在清空 {target_table} 的全天记录: {formatted_date}")
                async with self.clickhouse_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(sql)
            else:
                # 定向清理模式
                if not stock_codes:
                    logger.info(f"✅ 定向清理列表为空，无需操作 ({formatted_date})")
                    return True
                
                # 检查删除比例 (如果超过市场 10% 且未强制，则拦截)
                try:
                    all_stocks = await self.stock_universe.get_all_a_stocks()
                    if len(stock_codes) > len(all_stocks) * 0.1 and not force_all:
                        logger.error(f"❌ [Safety Valve] 拒绝大范围清理 ({len(stock_codes)} 只股票)，超过市场 10% 阈值")
                        return False
                except Exception as e:
                    logger.warning(f"⚠️ 无法获取市场总量，跳过安全阈值检查: {e}")

                # 分批执行定向清理
                batch_size = 500
                logger.warning(f"🗑️ [Batch Purge] 正在从 {target_table} 清理 {len(stock_codes)} 只个股: {formatted_date}")
                for i in range(0, len(stock_codes), batch_size):
                    batch = stock_codes[i:i+batch_size]
                    cleaned_batch = [clean_stock_code(c) for c in batch]
                    codes_str = ",".join([f"'{c}'" for c in cleaned_batch])
                    
                    sql = f"""
                    ALTER TABLE stock_data.{target_table} ON CLUSTER stock_cluster
                    DELETE WHERE trade_date = '{formatted_date}' 
                      AND stock_code IN ({codes_str})
                    """
                    async with self.clickhouse_pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            await cursor.execute(sql)
            
            logger.info(f"✅ 清理指令已下发至 ClickHouse.")
            return True

        except Exception as e:
            logger.error(f"❌ 清理数据失败: {e}", exc_info=True)
            return False

    # --- Delegated Methods (Compatible with sync_tick.py) ---

    async def fetch_sync_list(
        self, 
        scope: str, 
        shard_index: Optional[int] = None, 
        shard_total: Optional[int] = 3,
        trade_date: Optional[str] = None
    ) -> List[str]:
        """
        根据范围和分片参数获取待同步的股票列表
        统一从 StockUniverseService 获取，确保名单标准化（去 BJ/去重/排序）
        """
        if scope == "all":
            if trade_date:
                # 优先级：如果是历史日期，尝试从 K 线数据获取当日实际有成交的名单
                # 这比直接拿全市场名单更精准，且能过滤掉未上市或停牌股票
                stocks = await self.stock_universe.get_today_traded_stocks(trade_date)
            else:
                # 默认获取全市场名单 (Redis/MySQL source)
                stocks = await self.stock_universe.get_all_a_stocks()
            
            # [New V4.0] 自动从待处理名单中剔除停牌股，从源头减少无效补采
            if trade_date:
                try:
                    suspended = await self.stock_universe.get_suspended_stocks(trade_date)
                    before_count = len(stocks)
                    if suspended:
                        suspended_set = set(suspended)
                        stocks = [s for s in stocks if s not in suspended_set]
                        if before_count > len(stocks):
                            logger.info(f"🛡️ 从待执行名单中剔除 {before_count - len(stocks)} 只停牌股票 ({trade_date})，剩余 {len(stocks)} 只")
                        else:
                            logger.info(f"📍 名单中未包含停牌股票，无需剔除 (原始总数: {before_count})")
                    else:
                        logger.info(f"📍 未发现当日停牌股票数据 ({trade_date})，原始总数: {before_count}")
                except Exception as e:
                    logger.warning(f"⚠️ 过滤停牌股失败 (跳过): {e}")

            # 分片过滤
            if shard_index is not None and shard_total:
                return self.stock_universe._shard_filter(stocks, shard_index, shard_total)
            return stocks
            
        else:
            # 获取范围名单 (通常是配置好的 stock_list 或 passed_codes)
            # 如果是 passed_codes，它在 main 中已经处理过，这里只是兜底
            return await self.stock_universe.get_all_a_stocks()

    async def get_sharded_stocks(self, shard_index: int) -> List[str]:
        """Obsolete: Use fetch_sync_list instead"""
        return await self.stock_universe.get_shard_stocks(shard_index)

    async def get_stocks_from_kline_or_fallback(self, trade_date: str) -> list:
        """Obsolete: Use fetch_sync_list instead"""
        return await self.stock_universe.get_today_traded_stocks(trade_date)

    async def get_stock_pool(self) -> List[str]:
        """Obsolete: Use fetch_sync_list instead"""
        return await self.stock_universe.get_all_a_stocks()

    async def push_tasks_to_redis(self, stock_codes: List[str]) -> int:
        return await self.task_queue.push(stock_codes)

    async def consume_task_from_redis(self) -> Optional[str]:
        return await self.task_queue.consume()

    async def ack_task_in_redis(self, stock_code: str) -> bool:
        return await self.task_queue.ack(stock_code)

    async def recover_processing_tasks(self) -> List[str]:
        return await self.task_queue.recover()

    async def filter_stocks_need_repair(self, stock_codes: list, trade_date: str) -> list:
        return await self.validator.filter_need_repair(stock_codes, trade_date)

    async def sync_stock(self, stock_code: str, trade_date: str, force: bool = False, idempotent: bool = False) -> int:
        """
        同步单只股票分笔数据
        :param idempotent: 是否先清理旧数据 (默认 False，安全优先)
        """
        """同步单只股票 (Orchestration Logic)"""
        # 0. init status
        await self.tracker.update(stock_code, trade_date, "processing")
        
        try:
            # 1. Pre-validation (Skip if quality is good AND not forcing)
            if not force:
                is_valid = await self.validator.check_quality(stock_code, trade_date)
                if is_valid:
                    logger.debug(f"⏭️ {stock_code} 已跳过 (数据合格)")
                    await self.tracker.update(stock_code, trade_date, "skipped", 0)
                    return -1

            # 2. Fetch
            tick_data = await self.fetcher.fetch(stock_code, trade_date)
            
            if not tick_data:
                await self.tracker.update(stock_code, trade_date, "completed", 0)
                return 0

            # 3. Post-validation (Canary)
            self.validator.validate_canary(stock_code, tick_data, trade_date)
            
            # 4. Write
            count = await self.writer.write(stock_code, trade_date, tick_data, idempotent=idempotent)
            
            # 5. Update Status
            times = [x.get('time', '') for x in tick_data]
            min_t, max_t = min(times), max(times)
            await self.tracker.update(stock_code, trade_date, "completed", count, min_t, max_t)
            
            logger.debug(f"✓ {stock_code}: {count} ticks")
            return count

        except Exception as e:
            logger.error(f"❌ {stock_code} sync failed: {e}")
            await self.tracker.update(stock_code, trade_date, "failed", error=str(e))
            return 0

    async def sync_stocks(
        self, 
        stock_codes: List[str], 
        trade_date: Optional[str] = None,
        concurrency: int = 3,
        force: bool = False,
        idempotent: bool = False
    ) -> Dict[str, Any]:
        """批量同步"""
        if trade_date is None:
            trade_date = datetime.now(CST).strftime("%Y%m%d")
            
        logger.info(f"开始批量同步: {len(stock_codes)} 只, 日期 {trade_date}, 并发 {concurrency}, 强制={force}, 幂等清理={idempotent}")
        
        # [Mutation Storm Fix]: 如果需要幂等同步，在这里进行一次性的批量清理。
        # 避免在 loop 中每只股票都发起一个 ALTER TABLE DELETE 任务导致 ClickHouse 队列阻塞。
        if idempotent and stock_codes:
            await self.purge_tick_data(trade_date, stock_codes)
            # 全量清理后，禁用单只股票的内部幂等清理，以提升插入吞吐量并保护数据库。
            idempotent = False
            
        semaphore = asyncio.Semaphore(concurrency)
        results_lock = asyncio.Lock()
        results = {"success": 0, "failed": 0, "skipped": 0, "total_records": 0, "errors": [], "failed_codes": []}
        
        async def _worker(code: str):
            async with semaphore:
                start_t = asyncio.get_running_loop().time()
                try:
                    count = await self.sync_stock(code, trade_date, force=force, idempotent=idempotent)
                    async with results_lock:
                        if count > 0:
                            results["success"] += 1
                            results["total_records"] += count
                        elif count == -1:
                            results["skipped"] += 1
                        else:
                            results["failed"] += 1 # count==0 usually means no data or error
                            results["failed_codes"].append(code)
                except Exception as e:
                    async with results_lock:
                        results["failed"] += 1
                        results["failed_codes"].append(code)
                        results["errors"].append(f"{code}: {e}")
                
                # Pacing
                elapsed = asyncio.get_running_loop().time() - start_t
                delay = max(0, self.DEFAULT_MIN_PACING_INTERVAL - elapsed)
                if delay > 0:
                    await asyncio.sleep(delay)

        tasks = [_worker(code) for code in stock_codes]
        await asyncio.gather(*tasks)
        
        logger.info(f"同步结果: {results}")
        return results

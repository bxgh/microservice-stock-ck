
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
from core.stock_roster_service import StockRosterService
from core.tick_validator import TickDataValidator
from core.tick_fetcher import TickFetcher
from core.tick_writer import TickWriter
from core.sync_status import SyncStatusTracker

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
        
        # Components (Initialized in initialize())
        self.task_queue: Optional[TickTaskQueue] = None
        self.roster: Optional[StockRosterService] = None
        self.validator: Optional[TickDataValidator] = None
        self.fetcher: Optional[TickFetcher] = None
        self.writer: Optional[TickWriter] = None
        self.tracker: Optional[SyncStatusTracker] = None

    async def initialize(self) -> None:
        """初始化资源及组件"""
        async with self._lock:
            # 1. Initialize Resources
            if self.clickhouse_pool is None:
                self.clickhouse_pool = await asynch.create_pool(
                    host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
                    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
                    database="stock_data",
                    user=os.getenv("CLICKHOUSE_USER", "default"),
                    password=os.getenv("CLICKHOUSE_PASSWORD", ""),
                    minsize=1,
                    maxsize=5
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
            self.roster = StockRosterService(
                self.redis_client, self.http_session, self.clickhouse_pool, self.mootdx_api_url
            )
            self.validator = TickDataValidator(self.clickhouse_pool)
            self.fetcher = TickFetcher(self.http_session, self.mootdx_api_url)
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

    # --- Delegated Methods (Compatible with sync_tick.py) ---

    async def get_sharded_stocks(self, shard_index: int) -> List[str]:
        return await self.roster.get_by_shard(shard_index)

    async def get_stocks_from_kline_or_fallback(self, trade_date: str) -> list:
        return await self.roster.get_from_kline(trade_date)

    async def get_stock_pool(self) -> List[str]:
        return await self.roster.get_from_config()

    async def push_tasks_to_redis(self, stock_codes: List[str]) -> int:
        return await self.task_queue.push(stock_codes)

    async def consume_task_from_redis(self) -> Optional[str]:
        return await self.task_queue.consume()

    async def ack_task_in_redis(self, stock_code: str) -> bool:
        return await self.task_queue.ack(stock_code)

    async def recover_processing_tasks(self) -> List[str]:
        return await self.task_queue.recover()

    async def filter_stocks_need_repair(self, stock_codes: list, trade_date: str, min_tick_count: int = 2000) -> list:
        return await self.validator.filter_need_repair(stock_codes, trade_date, min_tick_count)

    async def sync_stock(self, stock_code: str, trade_date: str) -> int:
        """同步单只股票 (Orchestration Logic)"""
        # 0. init status
        await self.tracker.update(stock_code, trade_date, "processing")
        
        try:
            # 1. Pre-validation
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
            count = await self.writer.write(stock_code, trade_date, tick_data)
            
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
        concurrency: int = 3
    ) -> Dict[str, Any]:
        """批量同步"""
        if trade_date is None:
            trade_date = datetime.now(CST).strftime("%Y%m%d")
            
        logger.info(f"开始批量同步: {len(stock_codes)} 只, 日期 {trade_date}, 并发 {concurrency}")
        
        semaphore = asyncio.Semaphore(concurrency)
        results = {"success": 0, "failed": 0, "skipped": 0, "total_records": 0, "errors": []}
        
        async def _worker(code: str):
            async with semaphore:
                start_t = asyncio.get_running_loop().time()
                try:
                    count = await self.sync_stock(code, trade_date)
                    if count > 0:
                        results["success"] += 1
                        results["total_records"] += count
                    elif count == -1:
                        results["skipped"] += 1
                    else:
                        results["failed"] += 1 # count==0 usually means no data or error
                except Exception as e:
                    results["failed"] += 1
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

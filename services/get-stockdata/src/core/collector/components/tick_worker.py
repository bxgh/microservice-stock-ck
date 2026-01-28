import asyncio
import logging
import os
from collections import deque
from datetime import datetime
from typing import List, Dict, Tuple, Any

import aiohttp
import pytz

from src.core.collector.components.writer import ClickHouseWriter
from gsd_shared.tick import TickFetcher, TickDeduplicator, clean_stock_code
from gsd_shared.tick.status import SyncStatusTracker

logger = logging.getLogger("IntradayTickCollector.TickWorker")
CST = pytz.timezone('Asia/Shanghai')

# 配置常量
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "5"))
FINGERPRINT_CACHE_SIZE = int(os.getenv("FINGERPRINT_CACHE_SIZE", "60000"))

class TickWorker:
    """
    分笔采集 Worker (Refactored to use gsd_shared)
    
    职责:
    - 轮询股票池获取实时分笔 (via shared Fetcher)
    - 内存指纹去重 (via shared Deduplicator)
    - 将数据交给 Writer (Local Buffered Writer)
    """
    
    def __init__(
        self,
        http_session: aiohttp.ClientSession,
        writer: ClickHouseWriter,
        stock_pool: List[str],
        semaphore: asyncio.Semaphore,
        mootdx_api_url: str,
        redis_client: Any = None
    ):
        self.http_session = http_session
        self.writer = writer
        self.stock_pool = stock_pool
        self.sem = semaphore
        self.redis = redis_client
        self.circuit_breaker = circuit_breaker
        
        # Shared Components
        self.fetcher = TickFetcher(http_session, mootdx_api_url, mode=TickFetcher.Mode.REALTIME)
        self.deduplicator = TickDeduplicator(cache_size=FINGERPRINT_CACHE_SIZE)
        self.tracker = SyncStatusTracker(redis_client)
        
        self.offsets: Dict[str, int] = {}
        self.is_running = False
        
    async def run(self, stop_event: asyncio.Event, is_trading_time_func):
        """运行分笔采集循环"""
        self.is_running = True
        logger.info(f"📊 Starting tick loop for {len(self.stock_pool)} stocks...")
        
        # 加载初始 Offsets (Centrally)
        today_str = datetime.now(CST).strftime('%Y%m%d')
        self.offsets = await self.tracker.load_offsets(self.stock_pool, today_str)
        logger.info(f"✅ Loaded offsets for {len(self.offsets)} stocks via Central Tracker")
        
        while not stop_event.is_set():
            if not is_trading_time_func():
                await asyncio.sleep(1) # 快速检查，避免长时间阻塞
                continue

            round_start = asyncio.get_running_loop().time()
            
            # 并发轮询
            tasks = [self.poll_stock(code) for code in self.stock_pool]
            await asyncio.gather(*tasks, return_exceptions=True)

            # 检查刷盘
            await self.writer.flush_if_needed()

            duration = asyncio.get_running_loop().time() - round_start
            wait_time = max(0, POLL_INTERVAL_SECONDS - duration)
            
            if wait_time > 0:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait_time)
                except asyncio.TimeoutError:
                    pass

        logger.info("📊 TickWorker stopped")

    async def poll_stock(self, code: str):
        """采集单只股票"""
        if self.circuit_breaker and not self.circuit_breaker.is_available():
            return

        async with self.sem:
            try:
                clean_code = clean_stock_code(code)
                start_offset = self.offsets.get(clean_code, 0)
                
                # Fetch with start offset
                ticks = await self.fetcher.fetch(code, start=start_offset)
                if not ticks:
                    return

                new_rows = []
                today = datetime.now(CST).date()
                
                for item in ticks:
                    # Use Shared Deduplicator (Still useful for overlap safety)
                    if self.deduplicator.is_duplicate(clean_code, item):
                        continue
                        
                    # 解析数据
                    time_str = item.get('time', '')
                    price = float(item.get('price', 0))
                    volume = int(item.get('volume', item.get('vol', 0)))
                    direction_str = item.get('type', 'NEUTRAL')
                    direction = self._map_direction(direction_str)
                    
                    new_rows.append((
                        clean_code,
                        today,
                        time_str,
                        price,
                        volume,
                        price * volume,
                        direction
                    ))
            
                if new_rows:
                    await self.writer.add_ticks(new_rows)
                    
                    # Update Offset only after writer accepts data
                    count = len(ticks) # Use total retrieved count, not just filtered ones
                    new_offset = start_offset + count
                    self.offsets[clean_code] = new_offset
                    
                    # Persist to Redis (Centrally)
                    today_str = today.strftime('%Y%m%d')
                    await self.tracker.save_offset(clean_code, today_str, new_offset)
                    
            except Exception as e:
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                # logger.warning(f"⚠️ Poll {code} failed: {repr(e)[:50]}")
                pass
            else:
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()

    def _map_direction(self, d: str) -> int:
        mapping = {"BUY": 0, "SELL": 1, "NEUTRAL": 2}
        return mapping.get(d, 2)

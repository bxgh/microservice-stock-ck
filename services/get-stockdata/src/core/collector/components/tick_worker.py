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

logger = logging.getLogger("IntradayTickCollector.TickWorker")
CST = pytz.timezone('Asia/Shanghai')

# 配置常量
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "5"))
FINGERPRINT_CACHE_SIZE = int(os.getenv("FINGERPRINT_CACHE_SIZE", "1500"))

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
        
        # Shared Components
        self.fetcher = TickFetcher(http_session, mootdx_api_url, mode=TickFetcher.Mode.REALTIME)
        self.deduplicator = TickDeduplicator(cache_size=FINGERPRINT_CACHE_SIZE)
        
        self.offsets: Dict[str, int] = {}
        self.is_running = False
        
    async def run(self, stop_event: asyncio.Event, is_trading_time_func):
        """运行分笔采集循环"""
        self.is_running = True
        logger.info(f"📊 Starting tick loop for {len(self.stock_pool)} stocks...")
        
        # 加载初始 Offsets
        await self._load_offsets()
        
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
        
    async def _load_offsets(self):
        """从 Redis 加载断点 Offsets"""
        if not self.redis:
            return
            
        today_str = datetime.now(CST).strftime('%Y%m%d')
        # 批量构建 Keys
        keys = [f"tick:offset:{today_str}:{clean_stock_code(code)}" for code in self.stock_pool]
        
        try:
            # 批量获取 (MGET)
            values = await self.redis.mget(keys)
            
            loaded_count = 0
            for code, val in zip(self.stock_pool, values):
                clean = clean_stock_code(code)
                if val:
                    self.offsets[clean] = int(val)
                    loaded_count += 1
                else:
                    self.offsets[clean] = 0
            
            logger.info(f"✅ Loaded offsets for {loaded_count}/{len(self.stock_pool)} stocks from Redis")
            
        except Exception as e:
            logger.error(f"❌ Failed to load offsets from Redis: {e}")

    async def poll_stock(self, code: str):
        """采集单只股票"""
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
                    
                    # Update Offset
                    count = len(ticks) # Use total retrieved count, not just filtered ones (as fetch is based on raw index)
                    self.offsets[clean_code] = start_offset + count
                    
                    # Persist to Redis (Fire and Forget)
                    if self.redis:
                        today_str = today.strftime('%Y%m%d')
                        key = f"tick:offset:{today_str}:{clean_code}"
                        asyncio.create_task(self.redis.set(key, self.offsets[clean_code], ex=86400)) # 24h expiry
                    
            except Exception as e:
                # logger.warning(f"⚠️ Poll {code} failed: {repr(e)[:50]}")
                pass

    def _map_direction(self, d: str) -> int:
        mapping = {"BUY": 0, "SELL": 1, "NEUTRAL": 2}
        return mapping.get(d, 2)

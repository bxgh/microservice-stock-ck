import asyncio
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

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
        redis_client: Any = None,
        circuit_breaker: Optional[Any] = None
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
        
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
        self.bootstrapped_stocks: set = set() # 记录已完成启动接轨的个股
        self.is_running = False
        
    async def run(self, stop_event: asyncio.Event, is_trading_time_func):
        """运行分笔采集循环"""
        self.is_running = True
        logger.info(f"📊 Starting tick loop for {len(self.stock_pool)} stocks...")
        
        # 加载初始 Checkpoints (NEW: 包含位点与特征指纹)
        today_str = datetime.now(CST).strftime('%Y%m%d')
        self.checkpoints = await self.tracker.load_checkpoints(self.stock_pool, today_str)
        logger.info(f"✅ Loaded checkpoints for {len(self.checkpoints)} stocks. Ready for bootstrap.")
        
        while not stop_event.is_set():
            if not is_trading_time_func():
                await asyncio.sleep(1) # 快速检查，避免长时间阻塞
                continue

            round_start = asyncio.get_running_loop().time()
            
            # 并发轮询
            # 修复：分块执行以避免大量任务进入 Event Loop 导致拥塞
            # 引导阶段调小批次并增加间隙，防止撑爆 mootdx-api 连接池
            is_bootstrapping = len(self.bootstrapped_stocks) < len(self.stock_pool)
            batch_size = 10 if is_bootstrapping else 50
            
            for i in range(0, len(self.stock_pool), batch_size):
                chunk = self.stock_pool[i : i + batch_size]
                tasks = [self.poll_stock(code) for code in chunk]
                # 执行当前分块任务
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # 引导阶段增加延迟，防止抢占快照通道
                if is_bootstrapping:
                    await asyncio.sleep(0.5)
                    if i % 100 == 0:
                        logger.info(f"⚡ Tick Gathering Progress: {min(i + batch_size, len(self.stock_pool))}/{len(self.stock_pool)}")

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
        """
        采集单只股票
        策略：启动接轨模式 (Backward Search) + 常态化实时模式 (Start=0)
        """
        if self.circuit_breaker and not self.circuit_breaker.is_available():
            return

        async with self.sem:
            try:
                # 0. Reset local counters for this batch
                self.deduplicator.reset_batch_counters()
                
                clean_code = clean_stock_code(code)
                checkpoint = self.checkpoints.get(clean_code, {"offset": 0, "last_fp": ""})
                last_fp = checkpoint.get("last_fp", "")
                
                is_bootstrap = clean_code not in self.bootstrapped_stocks
                all_raw_ticks = []
                
                # --- 核心接轨逻辑 ---
                if is_bootstrap and last_fp:
                    # 引导阶段：深度向后回溯直到发现重复或到达深度极限 (10x200=2000行)
                    current_start = 0
                    found_anchor = False
                    
                    while current_start < 2000 and not found_anchor:
                        batch = await self.fetcher.fetch(code, start=current_start)
                        if not batch:
                            break
                        
                        # 必须从旧到新处理以便正确计算 occurrence 序号
                        # 且每次 fetch 的 batch 都需要独立的 occurrence counter？
                        # 不，是在逻辑上模拟从开盘到现在的过程。
                        # 但由于我们是 Backward 回溯，我们其实不知道前面的 occurrence 数量。
                        # [TRICK] 在引导模式下，如果 API 没给 num，我们就依赖 MD5 匹配基础字段。
                        # 或者我们强制在这个 batch 内使用 oldest-first 顺序。
                        for item in reversed(batch):
                            fp = self.deduplicator._make_key(item, increment=False)
                            if fp == last_fp:
                                found_anchor = True
                                break
                            all_raw_ticks.append(item)
                        
                        if found_anchor or len(batch) < 100:
                            break
                        current_start += 200
                    
                    self.bootstrapped_stocks.add(clean_code)
                else:
                    # 常态化模式：始终拉取最新一页 (start=0)
                    all_raw_ticks = await self.fetcher.fetch(code, start=0)
                    if is_bootstrap:
                        self.bootstrapped_stocks.add(clean_code)

                if not all_raw_ticks:
                    return

                new_rows = []
                today = datetime.now(CST).date()
                
                # 处理新数据（从旧到新反转处理，确保指纹入队顺序更符合时间演进）
                batch_latest_fp = last_fp
                for item in reversed(all_raw_ticks):
                    # 获取该条目的唯一指纹 (内含 num 分配逻辑)
                    fp = self.deduplicator._make_key(item)
                    
                    if self.deduplicator.is_duplicate_by_key(clean_code, fp):
                        continue
                    
                    batch_latest_fp = fp # 记录最新一条成功处理的指纹
                        
                    # 解析数据
                    # --- 价格纠偏逻辑: 针对基金类标的 (ETF/LOF) 的 10 倍偏移执行位移 ---
                    is_fund = any(clean_code.startswith(p) for p in ['51', '52', '56', '58', '59', '15', '16', '18'])
                    scale = 0.1 if is_fund else 1.0
                    
                    price = float(item.get('price', 0)) * scale
                    volume = int(item.get('volume', item.get('vol', 0)))
                    time_str = item.get('time', '')
                    iopv = float(item.get('iopv', 0)) * scale
                    direction_str = item.get('type', 'NEUTRAL')
                    direction = self._map_direction(direction_str)
                    
                    num = int(item.get('num', 0))
                    
                    new_rows.append((
                        clean_code, today, time_str, price, iopv, volume, 
                        price * volume, direction, num
                    ))
            
                if new_rows:
                    await self.writer.add_ticks(new_rows)
                    
                    # 记录并持久化到 Redis
                    today_str = today.strftime('%Y%m%d')
                    await self.tracker.save_checkpoint(clean_code, today_str, 0, batch_latest_fp)
                    self.checkpoints[clean_code] = {"offset": 0, "last_fp": batch_latest_fp}
                    
            except Exception:
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                logger.warning(f"⚠️ Poll {code} failed: {e}")
            else:
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()

    def _map_direction(self, d: str) -> int:
        mapping = {"BUY": 0, "SELL": 1, "NEUTRAL": 2}
        return mapping.get(d, 2)

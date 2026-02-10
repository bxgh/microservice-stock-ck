import asyncio
import logging
from datetime import datetime
from typing import List, Tuple, Any

import aiohttp
import pytz

from src.core.collector.components.writer import ClickHouseWriter
from gsd_shared.tick import clean_stock_code

logger = logging.getLogger("IntradayTickCollector.SnapshotWorker")
CST = pytz.timezone('Asia/Shanghai')

class SnapshotWorker:
    """
    快照采集 Worker
    
    职责:
    - 维护快照批次 (snapshot_batches)
    - 执行高频并行采集循环
    - 将数据交给 Writer
    """
    
    def __init__(
        self,
        http_session: aiohttp.ClientSession,
        writer: ClickHouseWriter,
        stock_pool: List[str],
        semaphore: asyncio.Semaphore,
        mootdx_api_url: str,
        batch_size: int = 80,
        interval: float = 3.0,
        circuit_breaker: Any = None,
        max_retries: int = 3
    ):
        self.http_session = http_session
        self.writer = writer
        self.sem = semaphore
        self.mootdx_api_url = mootdx_api_url
        self.interval = interval
        self.circuit_breaker = circuit_breaker
        self.max_retries = max_retries
        
        # 预计算批次
        self.batches = [
            stock_pool[i:i + batch_size]
            for i in range(0, len(stock_pool), batch_size)
        ]
        logger.info(f"📸 SnapshotWorker initialized: {len(self.batches)} batches (size={batch_size})")
        
        self.is_running = False
        
    async def run(self, stop_event: asyncio.Event, is_trading_time_func):
        """运行快照采集循环"""
        self.is_running = True
        logger.info(f"📸 Starting snapshot loop (interval={self.interval}s)...")
        
        while not stop_event.is_set():
            if not is_trading_time_func():
                await asyncio.sleep(60) # 非交易时间休眠
                continue

            start_time = asyncio.get_running_loop().time()
            
            try:
                # 执行并发采集
                await self._collect_snapshots()
            except Exception as e:
                logger.error(f"❌ Snapshot loop error: {e}")
                
            # 控制频率
            elapsed = asyncio.get_running_loop().time() - start_time
            wait_time = max(0, self.interval - elapsed)
            if wait_time > 0:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait_time)
                except asyncio.TimeoutError:
                    pass  # 继续下一轮
            else:
                logger.debug(f"⚠️ Snapshot loop lagging: took {elapsed:.2f}s")

        logger.info("📸 SnapshotWorker stopped")

    async def _collect_snapshots(self):
        """并行采集所有批次"""
        if not self.batches:
            return
            
        today = datetime.now(CST).date()
        snapshot_time = datetime.now(CST)
        
        # 定义单批次任务
        async def fetch_batch(batch_idx: int, batch: List[str]):
            async with self.sem:
                try:
                    return await self._fetch_snapshot_batch(batch_idx, batch, today, snapshot_time)
                except Exception as e:
                    logger.warning(f"⚠️ Batch {batch_idx} failed: {repr(e)[:80]}")
                    return []

        # 并发执行
        tasks = [fetch_batch(i, batch) for i, batch in enumerate(self.batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_rows = []
        success_count = 0
        
        for res in results:
            if isinstance(res, list) and res:
                all_rows.extend(res)
                success_count += 1
        
        # 写入数据
        if all_rows:
            await self.writer.add_snapshots(all_rows)
            
        logger.info(f"📊 Snapshot: {len(all_rows)} rows from {success_count}/{len(self.batches)} batches")

    async def _fetch_snapshot_batch(self, batch_idx: int, batch: List[str], today: Any, snapshot_time: datetime) -> List[Tuple]:
        """单个批次的 HTTP 请求 (带有重试逻辑)"""
        if self.circuit_breaker and not self.circuit_breaker.is_available():
            return []

        codes_param = ",".join(batch)
        url = f"{self.mootdx_api_url}/api/v1/quotes?codes={codes_param}"
        
        for attempt in range(self.max_retries + 1):
            try:
                async with self.http_session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        rows = []
                        for item in data:
                            row = self._map_snapshot_row(item, today, snapshot_time)
                            if row:
                                rows.append(row)
                        
                        # 只要请求成功即记录成功 (即使 rows 为空，说明业务正常但无成交)
                        if self.circuit_breaker:
                            self.circuit_breaker.record_success()
                            
                        if not rows:
                            logger.info(f"ℹ️ Batch {batch_idx} returned 0 valid rows (API count: {len(data)})")
                        return rows
                    else:
                        logger.warning(f"⚠️ Snapshot API returned {resp.status} (Batch {batch_idx}, Attempt {attempt+1}/{self.max_retries+1})")
            except Exception as e:
                logger.warning(f"⚠️ Batch {batch_idx} fetch exception: {repr(e)[:100]} (Attempt {attempt+1}/{self.max_retries+1})")
            
            if attempt < self.max_retries:
                await asyncio.sleep(2 ** attempt)  # 指数退避
        
        # 只有在所有重试都失败后才记录熔断故障
        if self.circuit_breaker:
            self.circuit_breaker.record_failure()
        logger.error(f"❌ Batch {batch_idx} failed after {self.max_retries + 1} attempts. Stocks: {batch[:3]}...")
        return []

    def _map_snapshot_row(self, item: Any, trade_date: Any, snapshot_time: datetime) -> tuple:
        """映射数据行 (复用原逻辑)"""
        try:
            # 基础校验
            if not item or 'code' not in item:
                return None
                
            # 价格转换
            current_price = float(item.get('price', 0))
            if current_price <= 0:  # 过滤无效价格
                return None

            return (
                snapshot_time,
                trade_date,
                clean_stock_code(item['code']),
                item.get('name', ''),
                str(item.get('market', '')),  # market (Fixed: ClickHouse String column)
                current_price,
                float(item.get('open', 0)),
                float(item.get('high', 0)),
                float(item.get('low', 0)),
                float(item.get('last_close', 0)),
                float(item.get('bid1', 0)), int(item.get('bid_vol1', 0)),
                float(item.get('bid2', 0)), int(item.get('bid_vol2', 0)),
                float(item.get('bid3', 0)), int(item.get('bid_vol3', 0)),
                float(item.get('bid4', 0)), int(item.get('bid_vol4', 0)),
                float(item.get('bid5', 0)), int(item.get('bid_vol5', 0)),
                float(item.get('ask1', 0)), int(item.get('ask_vol1', 0)),
                float(item.get('ask2', 0)), int(item.get('ask_vol2', 0)),
                float(item.get('ask3', 0)), int(item.get('ask_vol3', 0)),
                float(item.get('ask4', 0)), int(item.get('ask_vol4', 0)),
                float(item.get('ask5', 0)), int(item.get('ask_vol5', 0)),
                int(item.get('volume', 0)),
                float(item.get('amount', 0)),
                float(item.get('turnover', 0)) if item.get('turnover') else 0.0
            ) 
        except Exception:
            return None

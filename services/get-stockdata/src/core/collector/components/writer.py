import asyncio
import logging
import os
from datetime import datetime
from typing import List, Tuple, Any, Optional

import pytz
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import traceback

logger = logging.getLogger("IntradayTickCollector.Writer")
CST = pytz.timezone('Asia/Shanghai')

# 常量定义
FLUSH_THRESHOLD = int(os.getenv("FLUSH_THRESHOLD", "3000"))
FLUSH_INTERVAL_SECONDS = float(os.getenv("FLUSH_INTERVAL_SECONDS", "5"))

class ClickHouseWriter:
    """
    ClickHouse 异步写入器
    
    职责:
    - 维护 Tick 和 Snapshot 的写缓冲
    - 提供线程安全的添加接口
    - 批量写入 ClickHouse
    """
    
    def __init__(self, pool: Any, table_name: str = "tick_data_intraday_local"):
        """
        初始化 Writer
        
        Args:
            pool: asynch ClickHouse 连接池
            table_name: 写入的目标表名 (local or distributed)
        """
        self.pool = pool
        self.table_name = table_name
        self._write_buffer: List[Tuple] = []
        self._buffer_lock = asyncio.Lock()
        self._last_flush_time = asyncio.get_running_loop().time()
        
    async def add_ticks(self, rows: List[Tuple]) -> None:
        """
        添加分笔数据到缓冲区
        
        Args:
            rows: 数据行列表 (Tuple)
        """
        if not rows:
            return
            
        async with self._buffer_lock:
            self._write_buffer.extend(rows)
            
    async def add_snapshots(self, rows: List[Tuple]) -> None:
        """
        直接写入快照数据 (快照通常直接批量写入，不共用 Tick 的缓冲逻辑)
        
        Args:
            rows: 快照数据行列表
            
        Note: 快照数据量大且独立，通常由 SnapshotWorker 收集完一批后直接调用写入，
              避免占用 Tick 的缓冲区或与其逻辑混淆。
        """
        if not rows:
            return
            
        # 快照数据独立写入逻辑 (复用原 _collect_snapshots 中的写入逻辑)
        try:
            async with self.pool.acquire() as conn:
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
                        rows
                    )
            # logger.info(f"📸 Snapshot: {len(rows)} records written")
        except Exception as e:
            logger.error(f"❌ Snapshot write failed: {e}")

    async def flush_if_needed(self) -> None:
        """检查条件并执行 Flush (供外部循环调用)"""
        current_time = asyncio.get_running_loop().time()
        should_flush = False
        buffer_size = 0
        
        # 快速检查（无锁）
        if not self._write_buffer:
            return

        async with self._buffer_lock:
            buffer_size = len(self._write_buffer)
            if buffer_size >= FLUSH_THRESHOLD or (current_time - self._last_flush_time) >= FLUSH_INTERVAL_SECONDS:
                should_flush = True
        
        if should_flush:
            await self.flush()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(f"⚠️ Flush retrying... attempt {retry_state.attempt_number}")
    )
    async def flush(self) -> None:
        """执行 Flush 操作"""
        rows_to_write = []
        
        async with self._buffer_lock:
            if not self._write_buffer:
                return
            rows_to_write = list(self._write_buffer)
            self._write_buffer.clear()
            self._last_flush_time = asyncio.get_running_loop().time()
            
        if not rows_to_write:
            return

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"""INSERT INTO {self.table_name} 
                        (stock_code, trade_date, tick_time, price, volume, amount, direction) VALUES""",
                        rows_to_write
                    )
            logger.info(f"💾 Flushed {len(rows_to_write)} ticks to ClickHouse ({self.table_name})")
        except Exception as e:
            logger.error(f"❌ Tick write failed: {e}\n{traceback.format_exc()}")
            # 回滚缓冲区 (如果需要严格不丢数据)
            # async with self._buffer_lock:
            #     self._write_buffer.extend(rows_to_write)
            raise e

    async def close(self) -> None:
        """关闭 Writer，执行最后一次 Flush"""
        if self._write_buffer:
            logger.info(f"🛑 Closing writer, flushing {len(self._write_buffer)} remaining ticks...")
            try:
                await self.flush()
            except Exception as e:
                logger.error(f"❌ Final flush failed: {e}")

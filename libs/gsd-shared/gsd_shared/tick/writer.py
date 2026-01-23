import logging
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
import pytz

from .constants import TABLE_INTRADAY_LOCAL, TABLE_HISTORY_LOCAL
from .utils import clean_stock_code

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class TickWriter:
    """
    Unified Tick Writer
    
    Responsibilities:
    1. Route data to correct LOCAL tables based on date
       - Today -> tick_data_intraday_local (high frequency)
       - History -> tick_data_local (archive)
    2. Normalize fields (Direction, Volume) using standard mapping
    """
    
    class Target(Enum):
        INTRADAY = "intraday"
        HISTORY = "history"
        
    def __init__(self, clickhouse_pool):
        """
        Args:
            clickhouse_pool: asynch pool instance
        """
        self.ch_pool = clickhouse_pool

    async def write(
        self, 
        stock_code: str, 
        trade_date: str, 
        data: List[Dict[str, Any]]
    ) -> int:
        """
        Write tick data to ClickHouse.
        Auto-determines target table based on date.
        
        Returns:
            Number of rows written
        """
        if not self.ch_pool or not data:
            return 0
            
        # 1. Determine Target Table
        today_str = datetime.now(CST).strftime("%Y%m%d")
        if trade_date == today_str:
            target_table = TABLE_INTRADAY_LOCAL
        else:
            target_table = TABLE_HISTORY_LOCAL
            
        try:
            # 2. Transform Data
            rows = []
            trade_date_obj = datetime.strptime(trade_date, "%Y%m%d").date()
            
            # Clean code (ensure no prefixes)
            clean_code = self._clean_code(stock_code)
            
            for item in data:
                # Time normalize (HH:MM -> HH:MM:00)
                time_str = str(item.get('time', '09:30'))
                if len(time_str) == 5: time_str += ":00"
                
                # Field Mapping
                price = float(item.get('price', 0))
                # Handle vol vs volume alias
                vol = int(item.get('volume', item.get('vol', 0)))
                # Handle direction string/int mapping
                direction = self._map_direction(item.get('type', item.get('buyorsell', 2)))
                
                rows.append((
                    clean_code,
                    trade_date_obj,
                    time_str,
                    price,
                    vol,
                    price * vol,  # amount approx
                    direction
                ))

            if not rows:
                return 0
                
            # 3. Insert into ClickHouse (Using LOCAL table)
            # Note: We write to LOCAL tables directly for performance and strict sharding control
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"INSERT INTO stock_data.{target_table} (stock_code, trade_date, tick_time, price, volume, amount, direction) VALUES",
                        rows
                    )
            
            return len(rows)
            
        except Exception as e:
            logger.error(f"Tick write failed for {stock_code} to {target_table}: {e}")
            raise

    def _map_direction(self, value: Any) -> int:
        """
        Map direction to UInt8 (0=Buy, 1=Sell, 2=Neutral)
        """
        # String case (from get-stockdata API parsing)
        if isinstance(value, str):
            mapping = {"BUY": 0, "SELL": 1, "NEUTRAL": 2}
            return mapping.get(value.upper(), 2)
            
        # Integer case (from mootdx direct or gsd-worker legacy)
        if isinstance(value, int):
            return value if value in [0, 1, 2] else 2
            
        return 2

    def _clean_code(self, code: str) -> str:
        """Sanitize stock code: remove sh/sz prefixes and dots"""
        return clean_stock_code(code)

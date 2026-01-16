"""
大宗交易采集器

从 AkShare (Cloud Port 8003) 获取大宗交易数据并存入 ClickHouse。
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asynch
import os

from core.cloud_sync_service import CloudSyncService

logger = logging.getLogger(__name__)

class BlockTradeCollector(CloudSyncService):
    """大宗交易采集器"""
    
    def __init__(self, clickhouse_pool):
        super().__init__()
        self.ch_pool = clickhouse_pool
        self.port = 8003
        self.db_name = os.getenv("CLICKHOUSE_DB", "stock_data")

    async def collect(self, stock_code: str, date: Optional[str] = None) -> int:
        """
        采集大宗交易数据
        
        API 返回示例:
        [
            {
                "trade_date": "2025-12-26",
                "price": 6.78,
                "volume": 410000.0,
                "amount": 2779800.0,
                "premium_rate": -5.15
            }
        ]
        """
        url = self._get_service_url(self.port, f"/api/v1/block_trade/{stock_code}")
        data = await self._fetch_api(url)
        
        if not data:
            logger.debug(f"No block trade data found for {stock_code}")
            return 0
            
        rows = data if isinstance(data, list) else [data]
        if not rows:
            return 0
            
        await self._save_to_clickhouse(stock_code, rows)
        return len(rows)

    async def _save_to_clickhouse(self, code: str, rows: List[Dict]):
        async with self.ch_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = f"""
                INSERT INTO {self.db_name}.stock_block_trade_local 
                (stock_code, trade_date, price, volume, amount, premium_rate, update_time)
                VALUES
                """
                
                values = []
                for row in rows:
                    trade_date = row.get("trade_date")
                    if not trade_date:
                        continue
                    
                    values.append((
                        code,
                        trade_date.replace("-", ""),
                        float(row.get("price", 0) or 0),
                        float(row.get("volume", 0) or 0),
                        float(row.get("amount", 0) or 0),
                        float(row.get("premium_rate", 0) or 0),
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} block trade records for {code}")

"""
融资融券采集器

从 AkShare (Cloud Port 8003) 获取融资融券数据并存入 ClickHouse。
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asynch
import os

from core.cloud_sync_service import CloudSyncService

logger = logging.getLogger(__name__)

class MarginCollector(CloudSyncService):
    """融资融券采集器"""
    
    def __init__(self, clickhouse_pool):
        super().__init__()
        self.ch_pool = clickhouse_pool
        self.port = 8003
        self.db_name = os.getenv("CLICKHOUSE_DB", "stock_data")

    async def collect(self, stock_code: str, date: Optional[str] = None) -> int:
        """
        采集融资融券数据
        
        API 返回示例:
        [
            {
                "trade_date": "2025-12-26",
                "margin_balance": 7945895277.0,
                "margin_buy": 284936742.0,
                "short_balance": 1089772538.0,
                "short_sell": 37521610.0
            }
        ]
        """
        url = self._get_service_url(self.port, f"/api/v1/margin/{stock_code}")
        data = await self._fetch_api(url)
        
        if not data:
            logger.debug(f"No margin data found for {stock_code}")
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
                INSERT INTO {self.db_name}.stock_margin_local 
                (stock_code, trade_date, margin_balance, margin_buy, short_balance, short_sell, update_time)
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
                        float(row.get("margin_balance", 0) or 0),
                        float(row.get("margin_buy", 0) or 0),
                        float(row.get("short_balance", 0) or 0),
                        float(row.get("short_sell", 0) or 0),
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} margin records for {code}")

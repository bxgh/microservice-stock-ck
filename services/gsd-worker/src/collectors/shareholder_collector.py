"""
Shareholder Data Collector

Fetches shareholder count history and top 10 holders from AkShare (Cloud Port 8003).
Stores data into stock_holder_count and stock_top_holders tables.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

from core.cloud_sync_service import CloudSyncService

logger = logging.getLogger(__name__)

class ShareholderCollector(CloudSyncService):
    """Shareholder Data Collector"""
    
    def __init__(self, clickhouse_pool):
        super().__init__()
        self.ch_pool = clickhouse_pool
        self.port = 8003
        self.db_name = os.getenv("CLICKHOUSE_DB", "stock_data")

    async def collect(self, stock_code: str, date: Optional[str] = None) -> Dict[str, int]:
        """
        Collect shareholder data
        
        API returns:
        {
          "holder_count_history": [...],
          "top10_holders": [...]
        }
        """
        url = self._get_service_url(self.port, f"/api/v1/shareholder/{stock_code}")
        data = await self._fetch_api(url)
        
        if not data:
            logger.debug(f"No shareholder data found for {stock_code}")
            return {"holder_count": 0, "top_holders": 0}
            
        # 1. Save Holder Count History
        holder_count_data = data.get("holder_count_history", [])
        saved_count = await self._save_holder_count(stock_code, holder_count_data)
        
        # 2. Save Top 10 Holders
        top_holders_data = data.get("top10_holders", [])
        saved_top = await self._save_top_holders(stock_code, top_holders_data)
        
        return {"holder_count": saved_count, "top_holders": saved_top}

    async def _save_holder_count(self, code: str, rows: List[Dict]) -> int:
        if not rows:
            return 0
            
        async with self.ch_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = f"""
                INSERT INTO {self.db_name}.stock_holder_count_local 
                (stock_code, report_date, holder_count, change, avg_market_cap, update_time)
                VALUES
                """
                
                values = []
                for row in rows:
                    report_date = row.get("date")
                    if not report_date:
                        continue
                    
                    values.append((
                        code,
                        report_date.replace("-", ""),
                        int(row.get("count", 0) or 0),
                        float(row.get("change", 0) or 0),
                        float(row.get("avg_market_cap", 0) or 0),
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} holder count records for {code}")
                    return len(values)
        return 0

    async def _save_top_holders(self, code: str, rows: List[Dict]) -> int:
        if not rows:
            return 0
            
        async with self.ch_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = f"""
                INSERT INTO {self.db_name}.stock_top_holders_local 
                (stock_code, report_date, rank, holder_name, hold_count, hold_pct, share_type, update_time)
                VALUES
                """
                
                values = []
                for row in rows:
                    # Use 'time' as report_date from API response
                    report_date = row.get("time")
                    if not report_date:
                        continue
                    
                    values.append((
                        code,
                        report_date.replace("-", ""),
                        int(row.get("rank", 0) or 0),
                        row.get("holder_name", ""),
                        float(row.get("hold_count", 0) or 0),
                        float(row.get("hold_pct", 0) or 0),
                        row.get("share_type", ""),
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} top holder records for {code}")
                    return len(values)
        return 0

"""
资金流向采集器

从 AkShare (Cloud Port 8003) 获取资金流向数据并存入 ClickHouse。
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asynch
import os

from core.cloud_sync_service import CloudSyncService

logger = logging.getLogger(__name__)

class CapitalFlowCollector(CloudSyncService):
    """资金流向采集器"""
    
    def __init__(self, clickhouse_pool):
        super().__init__()
        self.ch_pool = clickhouse_pool
        self.port = 8003
        self.db_name = os.getenv("CLICKHOUSE_DB", "stock_data")

    async def collect(self, stock_code: str, date: Optional[str] = None) -> int:
        """
        采集资金流向数据
        
        API 返回示例:
        [
          {
            "date": "2025-07-22",
            "close": 1441.02,
            "main_net_inflow": 781613248.0,
            "main_net_inflow_pct": 12.76,
            "super_large_net_inflow": 568975264.0,
             ...
          }
        ]
        """
        url = self._get_service_url(self.port, f"/api/v1/capital_flow/{stock_code}")
        data = await self._fetch_api(url)
        
        if not data:
            logger.debug(f"No capital flow data found for {stock_code}")
            return 0
            
        rows = [data] if isinstance(data, dict) else data
        if not rows:
            return 0
            
        await self._save_to_clickhouse(stock_code, rows)
        return len(rows)

    async def _save_to_clickhouse(self, code: str, rows: List[Dict]):
        async with self.ch_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = f"""
                INSERT INTO {self.db_name}.stock_capital_flow_local 
                (stock_code, trade_date, close, main_net_inflow, main_net_inflow_pct, 
                 super_large_net_inflow, large_net_inflow, medium_net_inflow, small_net_inflow, 
                 update_time)
                VALUES
                """
                
                values = []
                for row in rows:
                    trade_date = row.get("date")
                    if not trade_date:
                        continue
                        
                    values.append((
                        code,
                        trade_date,
                        float(row.get("close", 0) or 0),
                        float(row.get("main_net_inflow", 0) or 0),
                        float(row.get("main_net_inflow_pct", 0) or 0),
                        float(row.get("super_large_net_inflow", 0) or 0),
                        float(row.get("large_net_inflow", 0) or 0),
                        float(row.get("medium_net_inflow", 0) or 0),
                        float(row.get("small_net_inflow", 0) or 0),
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} capital flow records for {code}")

"""
估值指标采集器

从 AkShare (Cloud Port 8003) 获取估值指标并存入 ClickHouse。
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asynch
import os

from core.cloud_sync_service import CloudSyncService

logger = logging.getLogger(__name__)

class ValuationCollector(CloudSyncService):
    """估值指标采集器"""
    
    def __init__(self, clickhouse_pool):
        super().__init__()
        self.ch_pool = clickhouse_pool
        self.port = 8003
        self.db_name = os.getenv("CLICKHOUSE_DB", "stock_data")

    async def collect(self, stock_code: str, date: Optional[str] = None) -> int:
        """
        采集估值指标
        
        API 返回示例:
        {
            "name": "贵州茅台",
            "pe": 20.08,
            "pb": 7.62,
            "market_cap": 1730637437130.0,
            "price": 1382.0,
            "code": "600519"
        }
        """
        url = self._get_service_url(self.port, f"/api/v1/valuation/{stock_code}")
        data = await self._fetch_api(url)
        
        if not data:
            logger.debug(f"No valuation data found for {stock_code}")
            return 0
            
        # 封装为列表
        rows = [data] if isinstance(data, dict) else data
        if not rows:
            return 0
            
        await self._save_to_clickhouse(stock_code, rows, date)
        return len(rows)

    async def _save_to_clickhouse(self, code: str, rows: List[Dict], date: str = None):
        async with self.ch_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = f"""
                INSERT INTO {self.db_name}.stock_valuation_local 
                (stock_code, trade_date, pe, pb, ps, market_cap, price, update_time)
                VALUES
                """
                
                values = []
                for row in rows:
                    # 如果没有指定日期，使用当前日期
                    trade_date = date if date else datetime.now().strftime("%Y%m%d")
                    
                    values.append((
                        code,
                        trade_date,
                        float(row.get("pe", 0) or 0),
                        float(row.get("pb", 0) or 0),
                        float(row.get("ps", 0) or 0),
                        float(row.get("market_cap", 0) or 0),
                        float(row.get("price", 0) or 0),
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} valuation records for {code}")

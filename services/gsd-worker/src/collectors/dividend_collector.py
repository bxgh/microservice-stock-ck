"""
分红配股采集器

从 AkShare (Cloud Port 8003) 获取分红配股数据并存入 ClickHouse。
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asynch
import os

from core.cloud_sync_service import CloudSyncService

logger = logging.getLogger(__name__)

class DividendCollector(CloudSyncService):
    """分红配股采集器"""
    
    def __init__(self, clickhouse_pool):
        super().__init__()
        self.ch_pool = clickhouse_pool
        self.port = 8003
        self.db_name = os.getenv("CLICKHOUSE_DB", "stock_data")

    async def collect(self, stock_code: str, date: Optional[str] = None) -> int:
        """
        采集分红配股数据
        
        API 返回示例:
        [
            {
                "report_date": "2023-12-31",
                "plan_date": "2024-04-01",
                "bonus_share_ratio": 0.0,
                "cash_dividend_ratio": 30.87,
                "progress": "实施分配"
            }
        ]
        """
        url = self._get_service_url(self.port, f"/api/v1/dividend/{stock_code}")
        data = await self._fetch_api(url)
        
        if not data:
            logger.debug(f"No dividend data found for {stock_code}")
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
                INSERT INTO {self.db_name}.stock_dividend_local 
                (stock_code, report_date, plan_date, bonus_share_ratio, cash_dividend_ratio, progress, update_time)
                VALUES
                """
                
                values = []
                for row in rows:
                    report_date = row.get("report_date")
                    if not report_date:
                        continue
                    
                    # 处理 plan_date 可能为空字符串的情况
                    plan_date = row.get("plan_date")
                    if not plan_date or plan_date == "":
                        plan_date = None
                    
                    values.append((
                        code,
                        report_date,
                        plan_date,
                        float(row.get("bonus_share_ratio", 0) or 0),
                        float(row.get("cash_dividend_ratio", 0) or 0),
                        row.get("progress", ""),
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} dividend records for {code}")

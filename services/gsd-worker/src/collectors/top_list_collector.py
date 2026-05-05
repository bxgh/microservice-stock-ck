"""
龙虎榜采集器

从 AkShare (Cloud Port 8003) 获取龙虎榜数据并存入 ClickHouse。
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asynch
import os

from core.cloud_sync_service import CloudSyncService

logger = logging.getLogger(__name__)

class TopListCollector(CloudSyncService):
    """龙虎榜采集器"""
    
    def __init__(self, clickhouse_pool):
        super().__init__()
        self.ch_pool = clickhouse_pool
        self.port = 8003
        self.db_name = os.getenv("CLICKHOUSE_DB", "stock_data")

    async def collect(self, stock_code: str = None, date: Optional[str] = None) -> int:
        """
        采集龙虎榜数据
        
        Note: 龙虎榜API通常是按日期获取全市场数据，不是单股票
        如果提供了 stock_code，会在结果中过滤
        
        API 返回示例:
        [
            {
                "code": "000628",
                "name": "高新发展",
                "close": 49.73,
                "change_pct": 9.9978,
                "turnover_rate": 32.2608,
                "net_buy": 92352744.86,
                "reason": "日涨幅偏离值达到7%的前5只证券"
            }
        ]
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        
        url = self._get_service_url(self.port, f"/api/v1/dragon_tiger/daily")
        data = await self._fetch_api(url, params={"date": date})
        
        if not data:
            logger.debug(f"No top list data found for {date}")
            return 0
            
        rows = data if isinstance(data, list) else [data]
        
        # 如果指定了股票代码，过滤结果
        if stock_code:
            rows = [r for r in rows if r.get("code") == stock_code]
        
        if not rows:
            return 0
            
        await self._save_to_clickhouse(rows, date)
        return len(rows)

    async def _save_to_clickhouse(self, rows: List[Dict], date: str):
        async with self.ch_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = f"""
                INSERT INTO {self.db_name}.stock_top_list_local 
                (stock_code, trade_date, reason, net_buy, turnover_rate, close_price, change_pct, update_time)
                VALUES
                """
                
                values = []
                for row in rows:
                    code = row.get("code")
                    if not code:
                        continue
                    
                    values.append((
                        code,
                        date,
                        row.get("reason", ""),
                        float(row.get("net_buy", 0) or 0),
                        float(row.get("turnover_rate", 0) or 0),
                        float(row.get("close", 0) or 0),
                        float(row.get("change_pct", 0) or 0),
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} top list records for {date}")

"""
财务数据采集器

从 AkShare (Cloud Port 8003) 获取个股财务数据并存入 ClickHouse。
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asynch
import os

from core.cloud_sync_service import CloudSyncService

logger = logging.getLogger(__name__)

class FinancialCollector(CloudSyncService):
    """财务数据采集器"""
    
    def __init__(self, clickhouse_pool):
        super().__init__()
        self.ch_pool = clickhouse_pool
        self.port = 8003
        self.db_name = os.getenv("CLICKHOUSE_DB", "stock_data")

    async def collect(self, stock_code: str, date: Optional[str] = None) -> int:
        """
        采集单只股票财务数据
        
        Args:
            stock_code: 股票代码 (e.g. 000001)
            date: (可选) 指定日期，API 可能仅支持获取最新或历史列表
            
        Returns:
            int: 插入记录数
        """
        # API 1: 核心财务指标 /api/v1/finance/{code}
        # 这里假设返回的是单个对象（最新）或列表（历史），根据文档示例返回的是单个对象
        # 如果需要历史，可能需要 /api/v1/finance/indicators/{code} 或类似
        # 根据 test_tencent_api_validate.py 验证结果，/api/v1/finance/600519 返回的是单个对象
        
        url = self._get_service_url(self.port, f"/api/v1/finance/{stock_code}")
        data = await self._fetch_api(url)
        
        if not data:
            logger.debug(f"No financial data found for {stock_code}")
            return 0
            
        # 封装为列表统一处理
        rows = [data] if isinstance(data, dict) else data
        
        if not rows:
            return 0
            
        await self._save_to_clickhouse(stock_code, rows)
        return len(rows)

    async def _save_to_clickhouse(self, code: str, rows: List[Dict]):
        """保存到 ClickHouse"""
        async with self.ch_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = f"""
                INSERT INTO {self.db_name}.stock_financial_local 
                (stock_code, report_date, total_revenue, net_profit, roe, earnings_per_share, update_time)
                VALUES
                """
                
                values = []
                for row in rows:
                    # 数据清洗与映射
                    # row example: {'total_revenue': 130904000000.0, 'net_profit': 64627000000.0, 'roe': 0.2464, 'report_date': '2025-09-30', 'code': '600519'}
                    report_date = row.get("report_date")
                    if not report_date:
                        continue
                        
                    values.append((
                        code,
                        report_date,
                        float(row.get("total_revenue", 0) or 0),
                        float(row.get("net_profit", 0) or 0),
                        float(row.get("roe", 0) or 0),
                        float(row.get("earnings_per_share", 0) or 0), # 假设 API 有这个字段，如果没有则为0
                        datetime.now()
                    ))
                
                if values:
                    await cursor.execute(query, values)
                    logger.info(f"Saved {len(values)} financial records for {code}")

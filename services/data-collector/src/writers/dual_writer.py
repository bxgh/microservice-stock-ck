import asyncio
import logging
from typing import List, Dict
from writers.clickhouse import ClickHouseWriter
from writers.mysql_cloud import MySQLCloudWriter

logger = logging.getLogger("data-collector.writers.dual_writer")

class DualWriter:
    """双写协调器 (ClickHouse + MySQL)"""
    
    def __init__(self, clickhouse: ClickHouseWriter, mysql: MySQLCloudWriter):
        self.clickhouse = clickhouse
        self.mysql = mysql

    async def initialize(self):
        """初始化内部写入器"""
        await asyncio.gather(
            self.clickhouse.initialize(),
            self.mysql.initialize()
        )

    async def close(self):
        """关闭内部写入器"""
        await asyncio.gather(
            self.clickhouse.close(),
            self.mysql.close()
        )

    async def write_kline(self, data: List[Dict]) -> Dict[str, int]:
        """平衡双写"""
        results = await asyncio.gather(
            self.clickhouse.write_kline(data),
            self.mysql.write_kline(data),
            return_exceptions=True
        )
        
        ck_count = results[0] if isinstance(results[0], int) else 0
        mysql_count = results[1] if isinstance(results[1], int) else 0
        
        if isinstance(results[0], Exception):
            logger.error(f"ClickHouse 写入异常: {results[0]}")
        if isinstance(results[1], Exception):
            logger.error(f"MySQL 写入异常: {results[1]}")
            
        return {
            "clickhouse": ck_count,
            "mysql": mysql_count
        }

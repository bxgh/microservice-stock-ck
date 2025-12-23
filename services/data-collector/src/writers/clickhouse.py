import logging
import asyncio
from clickhouse_driver import Client
from config.settings import settings
from typing import List, Dict

logger = logging.getLogger("data-collector.writers.clickhouse")

class ClickHouseWriter:
    """ClickHouse 数据写入器"""
    
    def __init__(self):
        self.client = None

    async def initialize(self):
        """初始化 ClickHouse 客户端"""
        if not self.client:
            try:
                self.client = Client(
                    host=settings.clickhouse_host,
                    port=settings.clickhouse_port,
                    user=settings.clickhouse_user,
                    password=settings.clickhouse_password,
                    database=settings.clickhouse_database
                )
                logger.info("✅ ClickHouse 客户端已初始化")
            except Exception as e:
                logger.error(f"❌ ClickHouse 初始化失败: {e}")
                raise

    async def write_kline(self, data: List[Dict]) -> int:
        """批量写入 K 线数据"""
        if not self.client:
            await self.initialize()
        if not data:
            return 0
            
        sql = """
        INSERT INTO stock_data.kline_daily 
        (stock_code, trade_date, open, high, low, close, volume, amount, turnover_rate, adj_factor) 
        VALUES
        """
        
        try:
            # 格式化数据为元组列表
            values = [
                (
                    row['stock_code'],
                    row['trade_date'],
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume'],
                    row['amount'],
                    row['turnover_rate'],
                    row['adj_factor']
                )
                for row in data
            ]
            
            # 使用 to_thread 避免阻塞事件循环
            await asyncio.to_thread(self.client.execute, sql, values)
            return len(values)
        except Exception as e:
            logger.error(f"❌ ClickHouse 写入失败: {e}")
            return 0
            
    async def close(self):
        """关闭连接"""
        if self.client:
            try:
                self.client.disconnect()
                logger.info("✅ ClickHouse 客户端已关闭")
            except Exception as e:
                logger.error(f"❌ ClickHouse 关闭出错: {e}")
            finally:
                self.client = None

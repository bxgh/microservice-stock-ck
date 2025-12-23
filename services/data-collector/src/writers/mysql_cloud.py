import logging
import aiomysql
from config.settings import settings
from typing import List, Dict

logger = logging.getLogger("data-collector.writers.mysql_cloud")

class MySQLCloudWriter:
    """腾讯云 MySQL 数据写入器"""
    
    def __init__(self):
        self.pool = None

    async def initialize(self):
        """初始化连接池"""
        if not self.pool and settings.mysql_host:
            try:
                self.pool = await aiomysql.create_pool(
                    host=settings.mysql_host,
                    port=settings.mysql_port,
                    user=settings.mysql_user,
                    password=settings.mysql_password,
                    db=settings.mysql_database,
                    minsize=5,  # 最小连接数
                    maxsize=settings.max_workers,  # 最大连接数与并发数一致
                    autocommit=True
                )
                logger.info(f"✅ 腾讯云 MySQL 连接池已初始化 (pool: 5-{settings.max_workers})")
            except Exception as e:
                logger.error(f"❌ 腾讯云 MySQL 连接失败: {e}")


    async def write_kline(self, data: List[Dict]) -> int:
        """写入 K 线数据到 MySQL"""
        if not self.pool:
            await self.initialize()
        
        if not self.pool or not data:
            return 0
            
        sql = """
        INSERT INTO kline_daily 
        (stock_code, trade_date, open, high, low, close, volume, amount, turnover_rate, adj_factor) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close),
        volume=VALUES(volume), amount=VALUES(amount), turnover_rate=VALUES(turnover_rate),
        adj_factor=VALUES(adj_factor)
        """
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
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
                    await cur.executemany(sql, values)
                    return len(values)
        except Exception as e:
            logger.error(f"❌ 腾讯云 MySQL 写入失败: {e}")
            return 0

    async def close(self):
        """关闭连接池"""
        if self.pool:
            try:
                self.pool.close()
                await self.pool.wait_closed()
                logger.info("✅ 腾讯云 MySQL 连接池已关闭")
            except Exception as e:
                logger.error(f"❌ 腾讯云 MySQL 关闭出错: {e}")
            finally:
                self.pool = None

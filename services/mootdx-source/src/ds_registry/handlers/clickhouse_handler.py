import logging
import asyncio
from asynch import connect
import pandas as pd
from typing import List, Dict, Any, Optional
from config import ClickHouseConfig

logger = logging.getLogger("unified-datasource")

class ClickHouseHandler:
    """
    ClickHouse 数据源处理器
    用于获取特征矩阵 (FeatureStore)
    """
    def __init__(self, config: ClickHouseConfig):
        self.config = config
        self._conn = None

    async def initialize(self) -> None:
        """初始化连接池"""
        try:
            self.pool = await asynch.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                minsize=1,
                maxsize=10
            )
            logger.info(f"✓ ClickHouse connection pool initialized ({self.config.host}:{self.config.port})")
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse pool: {e}")
            self.pool = None

    async def close(self) -> None:
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("ClickHouse connection pool closed")

    async def get_features(self, codes: List[str], date: str) -> pd.DataFrame:
        """从 FeatureStore 获取特征矩阵"""
        if not self.pool:
            logger.error("ClickHouse pool not initialized")
            return pd.DataFrame()

        if not codes:
            return pd.DataFrame()

        # 假设表名为 features, 包含字段 code, date, feature_vector
        query = "SELECT code, feature_vector FROM features WHERE date = %(date)s AND code IN %(codes)s"
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, {'date': date, 'codes': codes})
                    result = await cursor.fetchall()
                    # result 格式为 [('600519', [0.1, 0.2, ...]), ...]
                    return pd.DataFrame(result, columns=['code', 'feature_vector'])
        except Exception as e:
            logger.error(f"ClickHouse query error (features): {e}")
            return pd.DataFrame()

    async def get_tick_data(self, codes: List[str], date: str) -> pd.DataFrame:
        """从 ClickHouse 获取历史分笔数据 (作为 mootdx 的备份)"""
        if not self.pool:
            return pd.DataFrame()
            
        # 这里仅作占位，实际逻辑可根据需要完善
        query = "SELECT * FROM intraday_local WHERE date = %(date)s AND code IN %(codes)s"
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, {'date': date, 'codes': codes})
                    result = await cursor.fetchall()
                    return pd.DataFrame(result)
        except Exception as e:
            logger.error(f"ClickHouse query error (historical_tick): {e}")
            return pd.DataFrame()

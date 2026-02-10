import logging
import asyncio
import aiomysql
import pandas as pd
from typing import List, Dict, Any, Optional
from config import MySQLConfig

logger = logging.getLogger("unified-datasource")

class MySQLHandler:
    """
    MySQL 数据源处理器
    用于获取股票发行价、申万行业等基础数据
    """
    def __init__(self, config: MySQLConfig):
        self.config = config
        self.pool: Optional[aiomysql.Pool] = None

    async def initialize(self) -> None:
        """初始化连接池"""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                db=self.config.database,
                autocommit=True,
                minsize=2,
                maxsize=10
            )
            logger.info(f"✓ MySQL connection pool initialized ({self.config.host}:{self.config.port})")
        except Exception as e:
            logger.error(f"Failed to initialize MySQL pool: {e}")
            self.pool = None

    async def close(self) -> None:
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("MySQL connection pool closed")

    async def _normalize_codes(self, codes: List[str]) -> List[str]:
        """标准化代码：将 000001 转为 000001.SZ 或 000001.SH"""
        normalized = []
        for code in codes:
            if "." in code:
                normalized.append(code)
                continue
            # 通用规则：6 开头 SH，其他 SZ (简化处理)
            if code.startswith("6"):
                normalized.append(f"{code}.SH")
            else:
                normalized.append(f"{code}.SZ")
        return normalized

    async def fetch_issue_price_from_db(self, codes: List[str]) -> pd.DataFrame:
        """获取发行价 (从数据库 fetch)"""
        if not self.pool:
            logger.error("MySQL pool not initialized")
            return pd.DataFrame()

        if not codes:
            return pd.DataFrame()

        normalized_codes = await self._normalize_codes(codes)
        query = "SELECT ts_code as code, issue_price FROM stock_basic_info WHERE ts_code IN %s"
        logger.debug(f"Executing MySQL: {query} with {normalized_codes}")
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, (tuple(normalized_codes),))
                    result = await cur.fetchall()
                    logger.info(f"MySQL fetched {len(result)} issue price records")
                    return pd.DataFrame(result)
        except Exception as e:
            logger.error(f"MySQL FETCH ERROR (issue_price) [SQL: {query}]: {e}")
            return pd.DataFrame()

    async def fetch_sw_industry_from_db(self, codes: List[str], level: int = 3) -> pd.DataFrame:
        """获取申万行业分类 (从数据库 fetch)"""
        if not self.pool:
            logger.error("MySQL pool not initialized")
            return pd.DataFrame()

        if not codes:
            return pd.DataFrame()

        normalized_codes = await self._normalize_codes(codes)
        # 根据 level 选择返回的字段
        fields = ["code", "l1_code", "l1_name"]
        if level >= 2:
            fields.extend(["l2_code", "l2_name"])
        if level >= 3:
            fields.extend(["l3_code", "l3_name"])
            
        fields_str = ", ".join(fields)
        query = f"SELECT {fields_str} FROM stock_industry_sw WHERE code IN %s"
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, (tuple(normalized_codes),))
                    result = await cur.fetchall()
                    return pd.DataFrame(result)
        except Exception as e:
            logger.error(f"MySQL FETCH ERROR (sw_industry) [SQL: {query}]: {e}")
            return pd.DataFrame()

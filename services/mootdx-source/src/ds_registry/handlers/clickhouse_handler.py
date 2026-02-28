import logging
import asyncio
import asynch
import pandas as pd
from typing import List, Dict, Any, Optional
from config import ClickHouseConfig

logger = logging.getLogger("unified-datasource")

class ClickHouseHandler:
    """
    ClickHouse 数据源处理器
    用于获取特征矩阵 (FeatureStore) 和同花顺行业/概念数据
    """
    def __init__(self, config: ClickHouseConfig):
        self.config = config
        self.pool = None

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

    async def get_features(
        self, 
        codes: List[str], 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        从 FeatureStore 获取特征矩阵 (支持日期范围)
        并且将 feature_vector 数组展开为 f1, f2, ..., f9
        """
        if not self.pool:
            logger.error("ClickHouse pool not initialized")
            return pd.DataFrame()

        if not codes:
            return pd.DataFrame()

        # 展开数组并重命名
        feature_columns = ", ".join([f"feature_vector[{i+1}] as f{i+1}" for i in range(9)])
        query = f"""
            SELECT code as ts_code, date as trade_date, {feature_columns}
            FROM features 
            WHERE date >= %(start_date)s AND date <= %(end_date)s 
            AND code IN %(codes)s
            ORDER BY date ASC, code ASC
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, {
                        'start_date': start_date, 
                        'end_date': end_date, 
                        'codes': tuple(codes)
                    })
                    result = await cursor.fetchall()
                    cols = ['ts_code', 'trade_date'] + [f'f{i}' for i in range(1, 10)]
                    return pd.DataFrame(result, columns=cols)
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

    # ========== 同花顺行业/概念查询 ==========

    async def get_ths_industry(self, codes: List[str]) -> pd.DataFrame:
        """
        获取同花顺行业分类
        
        Returns:
            DataFrame: ts_code, l1_name, l2_name, l3_name
        """
        if not self.pool:
            logger.error("ClickHouse pool not initialized")
            return pd.DataFrame()
            
        if not codes:
            return pd.DataFrame()
            
        query = """
            SELECT stock_code as ts_code, l1_name, l2_name, l3_name 
            FROM stock_industry_ths 
            WHERE stock_code IN %(codes)s
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, {'codes': tuple(codes)})
                    result = await cursor.fetchall()
                    return pd.DataFrame(result, columns=['ts_code', 'l1_name', 'l2_name', 'l3_name'])
        except Exception as e:
            logger.error(f"ClickHouse query error (ths_industry): {e}")
            return pd.DataFrame()

    async def get_stock_concepts(self, codes: List[str]) -> pd.DataFrame:
        """
        获取股票所属的同花顺概念列表
        
        Returns:
            DataFrame: ts_code, sector_id, sector_name, sector_type
        """
        if not self.pool:
            logger.error("ClickHouse pool not initialized")
            return pd.DataFrame()
            
        if not codes:
            return pd.DataFrame()
        
        # 使用分布式表确保可见性
        query = """
            SELECT c.stock_code as ts_code, c.sector_id, s.sector_name, s.sector_type
            FROM stock_data.stock_sector_cons_ths c
            GLOBAL JOIN stock_data.stock_sector_ths s ON c.sector_id = s.sector_id
            WHERE c.stock_code IN %(codes)s
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, {'codes': tuple(codes)})
                    result = await cursor.fetchall()
                    return pd.DataFrame(result, columns=['ts_code', 'sector_id', 'sector_name', 'sector_type'])
        except Exception as e:
            logger.error(f"ClickHouse query error (stock_concepts): {e}")
            return pd.DataFrame()

    async def get_concept_stocks(self, concept_names: List[str]) -> pd.DataFrame:
        """
        根据概念名称获取成分股列表
        
        Returns:
            DataFrame: ts_code, sector_name
        """
        if not self.pool:
            logger.error("ClickHouse pool not initialized")
            return pd.DataFrame()
            
        if not concept_names:
            return pd.DataFrame()
        
        # 使用分布式表确保可见性
        query = """
            SELECT c.stock_code as ts_code, s.sector_name
            FROM stock_data.stock_sector_cons_ths c
            GLOBAL JOIN stock_data.stock_sector_ths s ON c.sector_id = s.sector_id
            WHERE s.sector_name IN %(names)s
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, {'names': tuple(concept_names)})
                    result = await cursor.fetchall()
                    return pd.DataFrame(result, columns=['ts_code', 'sector_name'])
        except Exception as e:
            logger.error(f"ClickHouse query error (concept_stocks): {e}")
            return pd.DataFrame()

    async def get_concept_member_counts(self) -> pd.DataFrame:
        """
        获取所有概念的成分股数量 (用于核心概念筛选)
        
        Returns:
            DataFrame: sector_id, sector_name, member_count
        """
        if not self.pool:
            logger.error("ClickHouse pool not initialized")
            return pd.DataFrame()
        
        # 使用分布式表确保可见性
        query = """
            SELECT s.sector_id, s.sector_name, COUNT(c.stock_code) as member_count
            FROM stock_data.stock_sector_ths s
            LEFT GLOBAL JOIN stock_data.stock_sector_cons_ths c ON s.sector_id = c.sector_id
            WHERE s.sector_type = 'concept'
            GROUP BY s.sector_id, s.sector_name
            ORDER BY member_count ASC
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)
                    result = await cursor.fetchall()
                    return pd.DataFrame(result, columns=['sector_id', 'sector_name', 'member_count'])
        except Exception as e:
            logger.error(f"ClickHouse query error (concept_member_counts): {e}")
            return pd.DataFrame()

    async def get_stocks_by_ths_industry(self, l3_name: str) -> pd.DataFrame:
        """
        根据同花顺三级行业获取所有成分股
        
        Args:
            l3_name: 同花顺三级行业名称
            
        Returns:
            DataFrame: ts_code, l1_name, l2_name, l3_name
        """
        if not self.pool:
            logger.error("ClickHouse pool not initialized")
            return pd.DataFrame()
            
        if not l3_name:
            return pd.DataFrame()
            
        query = """
            SELECT stock_code as ts_code, l1_name, l2_name, l3_name 
            FROM stock_data.stock_industry_ths 
            WHERE l3_name = %(l3_name)s
            ORDER BY stock_code ASC
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, {'l3_name': l3_name})
                    result = await cursor.fetchall()
                    return pd.DataFrame(result, columns=['ts_code', 'l1_name', 'l2_name', 'l3_name'])
        except Exception as e:
            logger.error(f"ClickHouse query error (stocks_by_ths_industry): {e}")
            return pd.DataFrame()

    async def get_stock_basic(self, codes: List[str]) -> pd.DataFrame:
        """
        获取股票基础信息 (从同步的元数据表)
        
        Args:
            codes: 股票代码列表, ["all"] 表示全量
            
        Returns:
            DataFrame: ts_code, name, industry, list_date, issue_price
        """
        if not self.pool:
            logger.error("ClickHouse pool not initialized")
            return pd.DataFrame()
            
        if codes == ["all"]:
            query = "SELECT stock_code, stock_code as code, name, industry, list_date, issue_price FROM stock_data.stock_basic_info"
            params = {}
        else:
            query = "SELECT stock_code, stock_code as code, name, industry, list_date, issue_price FROM stock_data.stock_basic_info WHERE stock_code IN %(codes)s"
            params = {'codes': tuple(codes)}
            
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params)
                    result = await cursor.fetchall()
                    cols = ['ts_code', 'code', 'name', 'industry', 'list_date', 'issue_price']
                    return pd.DataFrame(result, columns=cols)
        except Exception as e:
            logger.error(f"ClickHouse query error (stock_basic): {e}")
            return pd.DataFrame()

    async def get_valuation(self, codes: List[str]) -> pd.DataFrame:
        """
        获取最新估值数据 (从本地 ClickHouse)
        
        Returns:
            DataFrame: ts_code, trade_date, pe, pb, ps, market_cap, price
        """
        if not self.pool:
            return pd.DataFrame()
            
        if not codes:
            return pd.DataFrame()

        # 获取每个股票最新日期的估值
        query = """
            SELECT stock_code as ts_code, trade_date, pe, pb, ps, market_cap, price
            FROM stock_data.stock_valuation_local
            WHERE stock_code IN %(codes)s
            AND (stock_code, trade_date) IN (
                SELECT stock_code, MAX(trade_date)
                FROM stock_data.stock_valuation_local
                WHERE stock_code IN %(codes)s
                GROUP BY stock_code
            )
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, {'codes': tuple(codes)})
                    result = await cursor.fetchall()
                    cols = ['ts_code', 'trade_date', 'pe', 'pb', 'ps', 'market_cap', 'price']
                    return pd.DataFrame(result, columns=cols)
        except Exception as e:
            logger.error(f"ClickHouse query error (valuation): {e}")
            return pd.DataFrame()

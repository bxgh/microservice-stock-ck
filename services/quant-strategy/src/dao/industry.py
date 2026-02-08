import pandas as pd
from typing import List
from datasource.v1 import data_source_pb2
from .client import data_client

class IndustryDAO:
    """
    行业分类 DAO
    对应 GSF Part 1: IndustryDAO
    """
    
    async def get_sw_industry(self, codes: List[str], level: int = 3) -> pd.DataFrame:
        """
        获取申万行业分类
        
        Args:
            codes: 股票代码列表
            level: 行业级别 (1, 2, 3), 默认为 3级行业
            
        Returns:
            DataFrame: code, industry_name, industry_code
        """
        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_SW_INDUSTRY,
            codes,
            params={"level": str(level)}
        )
    
    async def get_ths_industry(self, codes: List[str]) -> pd.DataFrame:
        """
        获取同花顺行业分类
        
        Returns:
            DataFrame: ts_code, l1_name, l2_name, l3_name
        """
        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_THS_INDUSTRY,
            codes
        )
    
    async def get_stock_concepts(self, codes: List[str]) -> pd.DataFrame:
        """
        获取股票所属的同花顺概念板块
        
        Returns:
            DataFrame: ts_code, sector_id, sector_name, sector_type
        """
        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_THS_CONCEPTS,
            codes
        )

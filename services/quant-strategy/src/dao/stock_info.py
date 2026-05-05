import pandas as pd
from typing import List, Optional
from datasource.v1 import data_source_pb2
from .client import data_client

class StockInfoDAO:
    """
    股票基础信息 DAO
    对应 GSF Part 1: StockInfoDAO
    """
    
    async def get_stock_list(self) -> List[str]:
        """获取全市场股票代码列表"""
        df = await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_META, 
            ["all"]
        )
        if not df.empty and 'code' in df.columns:
            return df['code'].tolist()
        return []
        
    async def get_stock_meta(self, codes: List[str]) -> pd.DataFrame:
        """
        获取股票元数据 (代码, 名称, 上市日期等)
        """
        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_META,
            codes
        )
        
    async def get_issue_price(self, codes: List[str]) -> pd.DataFrame:
        """
        获取股票发行价
        
        Returns:
            DataFrame with columns: code, issue_price
        """
        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_ISSUE_PRICE,
            codes
        )

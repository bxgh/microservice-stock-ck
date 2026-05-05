"""
FeatureStoreDAO - 特征仓库 DAO
负责获取基于 Tick 计算的 9 维特征矩阵
"""
import pandas as pd
from typing import List, Optional
from datasource.v1 import data_source_pb2
from .client import data_client

class FeatureStoreDAO:
    """
    特征仓库 DAO
    对应 GSF Part 1: FeatureStoreDAO
    """
    
    async def get_features(
        self, 
        codes: List[str], 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        获取 9 维特征矩阵
        
        Args:
            codes: 股票代码列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            DataFrame: ts_code, trade_date, f1...f9
        """
        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_FEATURES,
            codes,
            params={
                "start_date": start_date,
                "end_date": end_date
            }
        )

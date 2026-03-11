import pandas as pd
from typing import List, Optional
from datasource.v1 import data_source_pb2
from .client import data_client

class FuturesDAO:
    """
    期货数据访问对象
    用于获取国际原油(WTI/Brent)等期货品种的历史及实时行情
    """
    
    async def get_futures_kline(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        获取期货历史K线数据
        
        Args:
            symbol: 品种代码 (如 "CL" 为 WTI, "OIL" 为 Brent)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            pd.DataFrame: 包含 trade_date, open_price, high_price, low_price, close_price, volume
        """
        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_FUTURES_KLINE_DAILY,
            [symbol],
            params={
                "start_date": start_date,
                "end_date": end_date
            }
        )

# 单例模式
futures_dao = FuturesDAO()

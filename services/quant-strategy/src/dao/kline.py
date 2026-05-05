import pandas as pd
from typing import List, Optional
from datasource.v1 import data_source_pb2
from .client import data_client

class KLineDAO:
    """
    K线与行情 DAO
    对应 GSF Part 1: KLineDAO
    """
    
    async def get_kline(
        self, 
        codes: List[str], 
        start_date: str, 
        end_date: str,
        frequency: str = "d",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取历史 K 线数据
        """
        #目前 mootdx-source 历史数据接口支持批量吗？根据 proto 是支持的。
        #但是底层 fetch_history_baostock 只取 codes[0]。
        #这里如果传入多个 code，可能需要循环调用或者服务端支持。
        #根据 gRPC 接口定义 DataRequest.codes 是 repeated string
        #如果服务端只处理第一个，客户端需要在这里做适配。
        #暂时假设服务端能处理，或者我们推荐一次只传一个 code 如果是日线以上。
        #通常策略是一个票一个票跑的。
        
        # 为了稳健性，如果是多个 code，暂建议上层循环调用，或者这里循环调用。
        # 但为了性能，这里先直接透传，看服务端表现。
        # (查看 mootdx-source service.py: _fetch_history_baostock: code = codes[0])
        # 服务端只处理第一个。所以这里如果 len(codes) > 1，需要循环。
        
        if len(codes) > 1:
            # 简单的客户端循环实现 (虽不高效，但功能正确)
            all_dfs = []
            for code in codes:
                df = await self.get_kline([code], start_date, end_date, frequency, adjust)
                if not df.empty:
                    all_dfs.append(df)
            if all_dfs:
                return pd.concat(all_dfs, ignore_index=True)
            return pd.DataFrame()

        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_HISTORY,
            codes,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "frequency": frequency,
                "adjust": adjust
            }
        )
        
    async def get_quotes(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        return await data_client.fetch_data(
            data_source_pb2.DATA_TYPE_QUOTES,
            codes
        )

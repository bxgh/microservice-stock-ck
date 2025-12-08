from typing import List, Dict, Optional, Union
import aiohttp
import pandas as pd
import logging
import json
import random
from config.settings import settings

logger = logging.getLogger(__name__)

class StockDataProvider:
    """
    数据适配层 (Adapter)
    
    负责与 get-stockdata 服务通信，获取行情和历史数据。
    支持 Redis 缓存（TODO）。
    """
    
    def __init__(self):
        self.base_url = settings.stockdata_service_url
        self.timeout = aiohttp.ClientTimeout(total=10)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def get_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情快照
        """
        if not codes:
            return pd.DataFrame()
            
        # 实际调用 API
        url = f"{self.base_url}/api/v1/quotes"
        try:
            # 暂时 mock，等待对接
            # async with self._session.get(url, params={"codes": ",".join(codes)}) as resp:
            #     data = await resp.json()
            #     return pd.DataFrame(data)
            
            # MOCK DATA for Development
            logger.debug(f"Mocking quotes for {len(codes)} stocks")
            return pd.DataFrame([
                {
                    "code": code, 
                    "price": round(random.uniform(5, 50), 2), 
                    "volume": random.randint(1000, 100000),
                    "change_pct": round(random.uniform(-10, 10), 2)
                } 
                for code in codes
            ])
            
        except Exception as e:
            logger.error(f"Failed to fetch quotes: {e}")
            return pd.DataFrame()

    async def get_history_bar(
        self, 
        code: str, 
        freq: str = "1d", 
        limit: int = 100
    ) -> pd.DataFrame:
        """
        获取历史K线
        """
        # MOCK DATA
        dates = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq="D")
        return pd.DataFrame({
            "date": dates,
            "open": [10.0] * limit,
            "high": [11.0] * limit,
            "low": [9.0] * limit,
            "close": [10.5] * limit,
            "volume": [10000] * limit
        })

    async def get_tick_data(self, code: str) -> pd.DataFrame:
        """获取分笔数据"""
        # MOCK IMPLEMENTATION
        return pd.DataFrame()

# 全局单例
data_provider = StockDataProvider()

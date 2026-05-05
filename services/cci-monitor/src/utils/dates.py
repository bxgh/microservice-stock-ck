from datetime import datetime, date, timedelta
from typing import List, Optional
import pandas as pd
from ..core.logger import cci_logger as logger

class TradingCalendar:
    """交易日历工具"""

    def __init__(self, data_client=None):
        self.data_client = data_client
        self._cache_dates: List[str] = []
        self._last_update: Optional[date] = None

    async def _refresh_calendar(self):
        """通过获取上证指数 K 线来刷新交易日历"""
        if self.data_client and (self._last_update != date.today()):
            try:
                # 获取过去一年的数据来构建日历
                start = (date.today() - timedelta(days=365)).isoformat()
                df = await self.data_client.fetch_kline("sh000001", start_date=start)
                if not df.empty:
                    self._cache_dates = sorted(df["date"].tolist())
                    self._last_update = date.today()
                    logger.info(f"📅 Trading calendar refreshed: {len(self._cache_dates)} days loaded.")
            except Exception as e:
                logger.error(f"Failed to refresh trading calendar: {e}")

    async def is_trading_day(self, dt: date) -> bool:
        """判断是否为交易日"""
        await self._refresh_calendar()
        dt_str = dt.isoformat()
        return dt_str in self._cache_dates

    async def get_last_trading_day(self, dt: Optional[date] = None) -> date:
        """获取指定日期之前的最后一个交易日"""
        await self._refresh_calendar()
        target = dt or date.today()
        target_str = target.isoformat()
        
        # 寻找小于等于 target_str 的最大日期
        last_day_str = None
        for d in reversed(self._cache_dates):
            if d <= target_str:
                last_day_str = d
                break
        
        if last_day_str:
            return date.fromisoformat(last_day_str)
        return target - timedelta(days=1)  # 回退

# 全局单例
trading_calendar = TradingCalendar()

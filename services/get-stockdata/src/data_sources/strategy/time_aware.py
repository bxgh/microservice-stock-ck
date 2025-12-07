# -*- coding: utf-8 -*-
"""
EPIC-007 时段感知策略

根据 A 股交易时段动态调整数据源优先级和缓存策略。

设计理由:
- 盘中 (09:25-15:00): 数据实时变化, 需要快速响应
- 盘后 (15:00-次日): 数据完整稳定, 适合复盘和缓存

@author: EPIC-007
@date: 2025-12-06
"""

from datetime import datetime, time, date
from enum import Enum
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

try:
    from chinese_calendar import is_workday, is_holiday
    HAS_CHINESE_CALENDAR = True
except ImportError:
    HAS_CHINESE_CALENDAR = False


class TradingSession(Enum):
    """交易时段"""
    PRE_MARKET = "pre_market"       # 盘前 (09:00-09:25)
    MORNING = "morning"              # 早盘 (09:30-11:30)
    NOON_BREAK = "noon_break"        # 午休 (11:30-13:00)
    AFTERNOON = "afternoon"          # 午盘 (13:00-15:00)
    POST_MARKET = "post_market"      # 盘后 (15:00-次日)
    NON_TRADING_DAY = "non_trading"  # 非交易日


class TimeAwareStrategy:
    """时段感知策略
    
    根据当前时段返回不同的数据源优先级和缓存 TTL。
    
    Example:
        strategy = TimeAwareStrategy()
        
        # 获取当前时段
        session = strategy.get_trading_session()
        
        # 获取行情数据的缓存 TTL
        ttl = strategy.get_cache_ttl("quotes")  # 盘中 3秒, 盘后 3600秒
        
        # 判断是否在交易时段
        if strategy.is_trading_hours():
            # 使用实时数据源
            ...
    """
    
    # 时区
    TIMEZONE = ZoneInfo("Asia/Shanghai")
    
    # 交易时段定义
    TRADING_TIMES = {
        "pre_market_start": time(9, 0),
        "pre_market_end": time(9, 25),
        "morning_start": time(9, 30),
        "morning_end": time(11, 30),
        "afternoon_start": time(13, 0),
        "afternoon_end": time(15, 0),
    }
    
    # 盘中数据源优先级
    INTRADAY_PRIORITY: Dict[str, List[str]] = {
        "quotes": ["mootdx", "easyquotation", "local_cache"],
        "tick": ["mootdx", "local_parquet"],
        "history": ["mootdx", "baostock", "clickhouse"],
        "ranking": ["akshare", "pywencai", "local_cache"],
        "sector": ["pywencai", "local_json"],
        "screening": ["pywencai"],
        "index": ["akshare", "local_json"],
    }
    
    # 盘后数据源优先级 (缓存优先)
    AFTERHOURS_PRIORITY: Dict[str, List[str]] = {
        "quotes": ["local_cache", "mootdx"],
        "tick": ["local_parquet", "mootdx"],
        "history": ["clickhouse", "mootdx", "baostock"],
        "ranking": ["pywencai", "local_cache"],  # pywencai 盘后数据更完整
        "sector": ["local_json", "pywencai"],
        "screening": ["pywencai"],
        "index": ["local_json", "akshare"],
    }
    
    # 缓存 TTL (秒)
    CACHE_TTL: Dict[str, Dict[str, int]] = {
        "quotes": {"intraday": 3, "afterhours": 3600},
        "tick": {"intraday": 2, "afterhours": 86400},
        "history": {"intraday": 86400, "afterhours": 86400},  # 历史数据不变
        "ranking": {"intraday": 300, "afterhours": 86400},     # 盘中5分钟
        "sector": {"intraday": 300, "afterhours": 86400},      # 板块涨幅5分钟
        "sector_constituents": {"intraday": 86400, "afterhours": 86400},  # 成分股不变
        "screening": {"intraday": 300, "afterhours": 86400},
        "index": {"intraday": 86400, "afterhours": 86400},     # 指数成分不变
    }
    
    def __init__(self, timezone: Optional[ZoneInfo] = None):
        """初始化
        
        Args:
            timezone: 时区, 默认 Asia/Shanghai
        """
        self._tz = timezone or self.TIMEZONE
    
    def get_now(self) -> datetime:
        """获取当前时间 (上海时区)"""
        return datetime.now(self._tz)
    
    def is_trading_day(self, d: Optional[date] = None) -> bool:
        """判断是否为交易日
        
        Args:
            d: 日期, 默认今天
        
        Returns:
            bool: 是否为交易日
        """
        d = d or self.get_now().date()
        
        # 周末一定不是交易日
        if d.weekday() >= 5:
            return False
        
        # 使用 chinese_calendar 判断节假日
        if HAS_CHINESE_CALENDAR:
            try:
                return is_workday(d) and not is_holiday(d)
            except Exception:
                pass
        
        # fallback: 工作日都是交易日
        return True
    
    def get_trading_session(self, dt: Optional[datetime] = None) -> TradingSession:
        """获取当前交易时段
        
        Args:
            dt: 时间, 默认当前时间
        
        Returns:
            TradingSession: 交易时段
        """
        dt = dt or self.get_now()
        
        # 非交易日
        if not self.is_trading_day(dt.date()):
            return TradingSession.NON_TRADING_DAY
        
        t = dt.time()
        
        # 根据时间判断时段
        if t < self.TRADING_TIMES["pre_market_start"]:
            return TradingSession.POST_MARKET  # 早上开盘前也算盘后
        elif t < self.TRADING_TIMES["pre_market_end"]:
            return TradingSession.PRE_MARKET
        elif t < self.TRADING_TIMES["morning_start"]:
            return TradingSession.PRE_MARKET
        elif t <= self.TRADING_TIMES["morning_end"]:
            return TradingSession.MORNING
        elif t < self.TRADING_TIMES["afternoon_start"]:
            return TradingSession.NOON_BREAK
        elif t <= self.TRADING_TIMES["afternoon_end"]:
            return TradingSession.AFTERNOON
        else:
            return TradingSession.POST_MARKET
    
    def is_trading_hours(self, dt: Optional[datetime] = None) -> bool:
        """判断是否在交易时段
        
        包括早盘、午盘和盘前集合竞价时段。
        
        Args:
            dt: 时间, 默认当前时间
        
        Returns:
            bool: 是否在交易时段
        """
        session = self.get_trading_session(dt)
        return session in (
            TradingSession.PRE_MARKET,
            TradingSession.MORNING,
            TradingSession.AFTERNOON,
        )
    
    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """判断是否在开盘时段 (可以正常交易)
        
        只包括早盘和午盘。
        
        Args:
            dt: 时间, 默认当前时间
        
        Returns:
            bool: 是否开盘
        """
        session = self.get_trading_session(dt)
        return session in (TradingSession.MORNING, TradingSession.AFTERNOON)
    
    def get_priority(self, data_type: str) -> List[str]:
        """获取数据类型的数据源优先级
        
        根据当前时段返回不同的优先级列表。
        
        Args:
            data_type: 数据类型 (quotes, tick, history, etc.)
        
        Returns:
            List[str]: 数据源名称列表, 按优先级排序
        """
        if self.is_trading_hours():
            return self.INTRADAY_PRIORITY.get(data_type, [])
        else:
            return self.AFTERHOURS_PRIORITY.get(data_type, [])
    
    def get_cache_ttl(self, data_type: str) -> int:
        """获取数据类型的缓存 TTL
        
        根据当前时段返回不同的 TTL。
        
        Args:
            data_type: 数据类型
        
        Returns:
            int: TTL (秒)
        """
        ttl_config = self.CACHE_TTL.get(data_type, {"intraday": 60, "afterhours": 3600})
        
        if self.is_trading_hours():
            return ttl_config.get("intraday", 60)
        else:
            return ttl_config.get("afterhours", 3600)
    
    def get_session_info(self) -> Dict:
        """获取当前时段信息 (用于调试/监控)"""
        now = self.get_now()
        session = self.get_trading_session(now)
        
        return {
            "current_time": now.isoformat(),
            "trading_day": self.is_trading_day(now.date()),
            "session": session.value,
            "is_trading_hours": self.is_trading_hours(now),
            "is_market_open": self.is_market_open(now),
        }


# 全局单例
_strategy_instance: Optional[TimeAwareStrategy] = None


def get_time_strategy() -> TimeAwareStrategy:
    """获取时段策略单例"""
    global _strategy_instance
    if _strategy_instance is None:
        _strategy_instance = TimeAwareStrategy()
    return _strategy_instance

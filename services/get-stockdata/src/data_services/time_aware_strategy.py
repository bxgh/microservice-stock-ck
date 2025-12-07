# -*- coding: utf-8 -*-
"""
时段感知策略 (TimeAwareStrategy)

根据A股交易时段提供智能的缓存TTL和数据源优先级策略。

交易时段:
- 09:15-09:25: 集合竞价
- 09:30-11:30: 上午连续竞价
- 11:30-13:00: 午休
- 13:00-15:00: 下午连续竞价
- 15:00-次日: 盘后

@author: EPIC-007 Story 007.07
@date: 2025-12-07
"""

from datetime import datetime, time
from typing import List, Literal
import pytz


# 交易时段类型
SessionType = Literal['pre_market', 'trading', 'lunch', 'after_hours']


class TimeAwareStrategy:
    """时段感知策略
    
    根据A股交易时段提供智能的缓存TTL和数据源优先级。
    
    Example:
        strategy = TimeAwareStrategy()
        
        if strategy.is_trading_hours():
            ttl = strategy.get_cache_ttl('quotes')  # 3秒
        else:
            ttl = strategy.get_cache_ttl('quotes')  # 3600秒
    """
    
    # A股交易时段配置
    TRADING_SESSIONS = {
        'pre_market': (time(9, 15), time(9, 25)),   # 集合竞价
        'morning': (time(9, 30), time(11, 30)),     # 上午连续竞价
        'lunch': (time(11, 30), time(13, 0)),       # 午休
        'afternoon': (time(13, 0), time(15, 0)),    # 下午连续竞价
    }
    
    # 缓存 TTL 配置 (秒)
    CACHE_TTL = {
        'quotes': {'trading': 3, 'after_hours': 3600},
        'tick': {'trading': 2, 'after_hours': 86400},
        'ranking': {'trading': 300, 'after_hours': 86400},
        'sector_ranking': {'trading': 300, 'after_hours': 86400},
        'sector_stocks': {'trading': 86400, 'after_hours': 86400},
        'history': {'trading': 86400, 'after_hours': 86400},
        'index_constituents': {'trading': 86400, 'after_hours': 86400},
        'etf_holdings': {'trading': 86400, 'after_hours': 86400},
    }
    
    # 数据源优先级
    SOURCE_PRIORITY = {
        'quotes': {
            'trading': ['mootdx', 'easyquotation'],
            'after_hours': ['local_cache', 'mootdx'],
        },
        'tick': {
            'trading': ['mootdx'],
            'after_hours': ['local_cache', 'mootdx'],
        },
        'ranking': {
            'trading': ['akshare', 'pywencai'],
            'after_hours': ['pywencai', 'local_cache'],
        },
        'sector': {
            'trading': ['pywencai'],
            'after_hours': ['local_cache', 'pywencai'],
        },
        'history': {
            'trading': ['baostock', 'mootdx'],
            'after_hours': ['baostock', 'mootdx'],
        },
    }
    
    def __init__(self, timezone: str = 'Asia/Shanghai'):
        """初始化
        
        Args:
            timezone: 时区，默认上海时间
        """
        self._tz = pytz.timezone(timezone)
    
    def _now(self) -> datetime:
        """获取当前时间"""
        return datetime.now(self._tz)
    
    def get_session(self) -> SessionType:
        """获取当前交易时段
        
        Returns:
            str: 'pre_market', 'trading', 'lunch', 'after_hours'
        """
        now = self._now()
        current_time = now.time()
        
        # 周末
        if now.weekday() >= 5:
            return 'after_hours'
        
        # 集合竞价
        start, end = self.TRADING_SESSIONS['pre_market']
        if start <= current_time < end:
            return 'pre_market'
        
        # 上午交易
        start, end = self.TRADING_SESSIONS['morning']
        if start <= current_time < end:
            return 'trading'
        
        # 午休
        start, end = self.TRADING_SESSIONS['lunch']
        if start <= current_time < end:
            return 'lunch'
        
        # 下午交易
        start, end = self.TRADING_SESSIONS['afternoon']
        if start <= current_time < end:
            return 'trading'
        
        # 其他时间
        return 'after_hours'
    
    def is_trading_hours(self) -> bool:
        """是否交易时段
        
        Returns:
            bool: True 表示盘中 (09:30-11:30, 13:00-15:00)
        """
        return self.get_session() == 'trading'
    
    def is_pre_market(self) -> bool:
        """是否集合竞价时段"""
        return self.get_session() == 'pre_market'
    
    def is_lunch_break(self) -> bool:
        """是否午休时段"""
        return self.get_session() == 'lunch'
    
    def is_after_hours(self) -> bool:
        """是否盘后"""
        return self.get_session() == 'after_hours'
    
    def get_cache_ttl(self, data_type: str) -> int:
        """获取缓存 TTL
        
        Args:
            data_type: 数据类型 ('quotes', 'tick', 'ranking', etc.)
            
        Returns:
            int: 缓存 TTL (秒)
        """
        config = self.CACHE_TTL.get(data_type, {'trading': 300, 'after_hours': 3600})
        
        if self.is_trading_hours() or self.is_pre_market():
            return config['trading']
        else:
            return config['after_hours']
    
    def get_source_priority(self, data_type: str) -> List[str]:
        """获取数据源优先级
        
        Args:
            data_type: 数据类型
            
        Returns:
            List[str]: 数据源列表，按优先级排序
        """
        config = self.SOURCE_PRIORITY.get(data_type, {'trading': [], 'after_hours': []})
        
        if self.is_trading_hours() or self.is_pre_market():
            return config.get('trading', [])
        else:
            return config.get('after_hours', [])
    
    def get_session_info(self) -> dict:
        """获取当前时段详情
        
        Returns:
            dict: 包含时段信息的字典
        """
        now = self._now()
        session = self.get_session()
        
        return {
            'time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'weekday': now.weekday(),
            'session': session,
            'is_trading': self.is_trading_hours(),
            'is_weekend': now.weekday() >= 5,
        }


# 全局单例 (线程安全)
import threading

_strategy_instance = None
_strategy_lock = threading.Lock()


def get_time_strategy() -> TimeAwareStrategy:
    """获取全局时段策略实例 (线程安全)"""
    global _strategy_instance
    if _strategy_instance is None:
        with _strategy_lock:
            # 双重检查锁定
            if _strategy_instance is None:
                _strategy_instance = TimeAwareStrategy()
    return _strategy_instance

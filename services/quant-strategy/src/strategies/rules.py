"""
具体的风控规则实现
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, time

from core.risk import RiskRule
from strategies.signal import Signal

logger = logging.getLogger(__name__)

class StaticBlacklistRule(RiskRule):
    """静态黑名单规则"""
    
    def __init__(self, blacklist: List[str]):
        self._blacklist = set(blacklist)
        
    @property
    def name(self) -> str:
        return "StaticBlacklistRule"
        
    async def check(self, signal: Signal, context: Dict[str, Any] = None) -> bool:
        if signal.stock_code in self._blacklist:
            logger.info(f"Risk Check Failed: {signal.stock_code} is in blacklist")
            return False
        return True
        
    def add_to_blacklist(self, stock_code: str):
        self._blacklist.add(stock_code)
        
    def remove_from_blacklist(self, stock_code: str):
        if stock_code in self._blacklist:
            self._blacklist.remove(stock_code)


class TradingHoursRule(RiskRule):
    """交易时间检查规则"""
    
    def __init__(self):
        # A股交易时间
        self.morning_start = time(9, 30)
        self.morning_end = time(11, 30)
        self.afternoon_start = time(13, 0)
        self.afternoon_end = time(15, 0)
        
    @property
    def name(self) -> str:
        return "TradingHoursRule"
        
    async def check(self, signal: Signal, context: Dict[str, Any] = None) -> bool:
        # 使用信号的时间戳，如果没有则使用当前时间
        check_time = None
        if signal.timestamp:
            if isinstance(signal.timestamp, datetime):
                check_time = signal.timestamp.time()
            elif isinstance(signal.timestamp, str):
                try:
                    check_time = datetime.fromisoformat(signal.timestamp).time()
                except ValueError:
                    pass
        
        if check_time is None:
            check_time = datetime.now().time()
            
        # 简单检查：如果在交易时间段内
        is_trading = (self.morning_start <= check_time <= self.morning_end) or \
                     (self.afternoon_start <= check_time <= self.afternoon_end)
                     
        if not is_trading:
            # 允许稍微的偏差 (比如收盘后几秒内的信号)
            # 这里严格执行，非交易时间不允许发信号
            logger.info(f"Risk Check Failed: Signal time {check_time} is outside trading hours")
            return False
            
        return True


class PriceLimitRule(RiskRule):
    """价格有效性检查规则"""
    
    @property
    def name(self) -> str:
        return "PriceLimitRule"
        
    async def check(self, signal: Signal, context: Dict[str, Any] = None) -> bool:
        if signal.price is None:
            # 市价单可能没有价格，视情况而定
            # 如果是限价单逻辑，通常需要价格
            # 这里假设必须有参考价格
            return True # 暂不强制
            
        if signal.price <= 0:
            logger.info(f"Risk Check Failed: Invalid price {signal.price}")
            return False
            
        # 可以在这里添加涨跌停检查逻辑 (需要昨收盘价)
        # context 中如果有 'pre_close'
        if context and 'pre_close' in context:
            pre_close = context['pre_close']
            if pre_close > 0:
                limit_up = round(pre_close * 1.1, 2)
                limit_down = round(pre_close * 0.9, 2)
                
                # 简单容错
                if not (limit_down * 0.95 <= signal.price <= limit_up * 1.05):
                     logger.warning(f"Risk Warning: Price {signal.price} deviates significantly from pre_close {pre_close}")
                     # 可以在这里决定是否拒绝
                     
        return True

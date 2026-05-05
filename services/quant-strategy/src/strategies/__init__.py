"""Strategies Package

量化策略引擎核心模块。

提供策略基类、信号数据结构和策略注册表。
"""

from models.signal import Signal

from .base_strategy import BaseStrategy
from .lead_lag_strategy import LeadLagStrategy
from .registry import StrategyRegistry

__all__ = [
    'Signal',
    'BaseStrategy',
    'StrategyRegistry',
    'LeadLagStrategy',
]

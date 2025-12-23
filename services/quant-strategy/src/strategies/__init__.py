"""Strategies Package

量化策略引擎核心模块。

提供策略基类、信号数据结构和策略注册表。
"""

from .base_strategy import BaseStrategy
from .registry import StrategyRegistry
from models.signal import Signal

__all__ = [
    'Signal',
    'BaseStrategy',
    'StrategyRegistry',
]

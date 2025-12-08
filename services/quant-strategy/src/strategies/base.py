from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
import pandas as pd

class SignalType(str, Enum):
    LONG = "LONG"       # 做多
    SHORT = "SHORT"     # 做空 (A股通常不涉及)
    CLOSE = "CLOSE"     # 平仓
    HOLD = "HOLD"       # 持有 (观望)

class SignalPriority(str, Enum):
    HIGH = "HIGH"       # 强力推荐 (如: 多个指标共振)
    MEDIUM = "MEDIUM"   # 普通推荐
    LOW = "LOW"         # 弱信号 (如: 仅用于观察)

class StrategySignal(BaseModel):
    """
    策略信号标准模型
    """
    strategy_name: str
    stock_code: str
    signal_type: SignalType
    priority: SignalPriority = SignalPriority.MEDIUM
    price: Optional[float] = None
    generated_time: datetime = datetime.now()
    reason: str = ""
    score: float = 0.0          # 信号得分 (0-100)
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True

class BaseStrategy(ABC):
    """
    策略基类
    
    所有具体的量化策略都应继承此类。
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.is_initialized = False
        
    async def initialize(self):
        """初始化策略 (加载数据、预计算等)"""
        self.is_initialized = True
        
    @abstractmethod
    async def on_bar(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        K线更新时触发 (如每日收盘)
        
        Args:
            data: 最新的K线数据 DataFrame
        """
        pass
        
    @abstractmethod
    async def on_tick(self, tick_data: Any) -> List[StrategySignal]:
        """
        Tick更新时触发 (实时盘中)
        
        Args:
            tick_data: 实时分笔/快照数据
        """
        pass
        
    async def shutdown(self):
        """清理资源"""
        pass

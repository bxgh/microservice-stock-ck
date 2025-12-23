"""
BaseStrategy 抽象基类

所有策略必须继承此类并实现其抽象方法。
支持两种模式:
1. 实时交易模式: generate_signals() + on_bar()/on_tick()
2. 批量扫描模式: evaluate() - 用于每日扫描
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd

from models.signal import Signal

logger = logging.getLogger(__name__)


class Timeframe(Enum):
    """策略时间周期"""
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"


class MarketRegime(Enum):
    """市场环境"""
    BULL = "bull"
    BEAR = "bear"
    RANGE = "range"


@dataclass
class StrategyResult:
    """策略评估结果
    
    用于每日扫描返回的评分结果。
    """
    strategy_id: str
    stock_code: str
    score: float  # 0-100
    passed: bool
    reason: str
    details: dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "stock_code": self.stock_code,
            "score": self.score,
            "passed": self.passed,
            "reason": self.reason,
            "details": self.details,
            "evaluated_at": self.evaluated_at.isoformat()
        }


class BaseStrategy(ABC):
    """
    策略抽象基类
    
    所有策略必须实现:
    - strategy_id: 策略唯一标识
    - evaluate(): 评估单只股票 (用于批量扫描)
    
    可选实现:
    - initialize(): 初始化策略
    - generate_signals(): 生成交易信号 (实时交易)
    - validate_parameters(): 验证策略参数
    """

    def __init__(self, name: str, parameters: dict[str, Any] | None = None):
        """
        初始化策略
        
        Args:
            name: 策略名称
            parameters: 策略参数
        """
        self.name = name
        self.parameters = parameters or {}
        self._initialized = False
        logger.info(f"Strategy {name} created with parameters: {self.parameters}")

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """策略唯一标识符"""
        pass
    
    @property
    def timeframe(self) -> Timeframe:
        """策略时间周期，默认日线"""
        return Timeframe.DAILY
    
    @property
    def preferred_regime(self) -> list[MarketRegime]:
        """策略适用的市场环境，默认所有环境"""
        return [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.RANGE]

    @abstractmethod
    async def evaluate(self, stock_code: str, data: dict[str, Any]) -> StrategyResult:
        """
        评估单只股票
        
        这是批量扫描模式的核心方法。ScannerEngine 会调用此方法
        对每只股票进行评估。
        
        Args:
            stock_code: 股票代码
            data: 股票数据快照，包含:
                - financials: 财务指标
                - valuation: 估值数据
                - price: 行情数据
                - factors: 预计算因子
                
        Returns:
            StrategyResult: 评估结果
        """
        pass

    async def initialize(self) -> None:
        """
        初始化策略 (可选)
        
        在策略运行前调用，用于加载配置、连接数据源等
        """
        self._initialized = True
        logger.info(f"Strategy {self.name} initialized")

    async def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """
        生成交易信号 (可选，用于实时交易)
        
        Args:
            data: 市场数据DataFrame
            
        Returns:
            Signal对象列表
        """
        return []

    def validate_parameters(self) -> bool:
        """
        验证策略参数 (可选)
        
        Returns:
            True if valid
        """
        return True

    async def on_bar(self, bar: dict[str, Any]) -> None:
        """K线数据回调 (可选实现)"""
        pass

    async def on_tick(self, tick: dict[str, Any]) -> None:
        """Tick数据回调 (可选实现)"""
        pass

    def get_info(self) -> dict[str, Any]:
        """获取策略信息"""
        return {
            'strategy_id': self.strategy_id,
            'name': self.name,
            'parameters': self.parameters,
            'timeframe': self.timeframe.value,
            'preferred_regime': [r.value for r in self.preferred_regime],
            'initialized': self._initialized,
            'class': self.__class__.__name__
        }

    def is_initialized(self) -> bool:
        """检查策略是否已初始化"""
        return self._initialized

    async def close(self) -> None:
        """关闭策略，释放资源"""
        self._initialized = False
        logger.info(f"Strategy {self.name} closed")

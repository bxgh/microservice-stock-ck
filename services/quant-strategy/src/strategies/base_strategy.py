"""
BaseStrategy 抽象基类

所有策略必须继承此类并实现其抽象方法
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
import logging

from models.signal import Signal

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    策略抽象基类
    
    所有策略必须实现:
    - initialize(): 初始化策略
    - generate_signals(): 生成交易信号
    - validate_parameters(): 验证策略参数
    """
    
    def __init__(self, name: str, parameters: Optional[Dict[str, Any]] = None):
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
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化策略
        
        在策略运行前调用，用于加载配置、连接数据源等
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    async def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 市场数据DataFrame
            
        Returns:
            Signal对象列表
            
        Raises:
            ValueError: 数据验证失败
        """
        pass
    
    @abstractmethod
    def validate_parameters(self) -> bool:
        """
        验证策略参数
        
        Returns:
            True if valid
            
        Raises:
            ValueError: 参数无效时抛出异常并说明原因
        """
        pass
    
    async def on_bar(self, bar: Dict[str, Any]) -> None:
        """
        K线数据回调 (可选实现)
        
        Args:
            bar: K线数据字典
        """
        pass
    
    async def on_tick(self, tick: Dict[str, Any]) -> None:
        """
        Tick数据回调 (可选实现)
        
        Args:
            tick: Tick数据字典
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取策略信息
        
        Returns:
            策略信息字典
        """
        return {
            'name': self.name,
            'parameters': self.parameters,
            'initialized': self._initialized,
            'class': self.__class__.__name__
        }
    
    async def _mark_initialized(self) -> None:
        """标记策略已初始化"""
        self._initialized = True
        logger.info(f"Strategy {self.name} initialized")
    
    async def backtest(self, signals: List[Signal]) -> 'BacktestResult':
        """
        回测策略信号
        
        Args:
            signals: 信号列表
            
        Returns:
            BacktestResult对象
        """
        from backtest.vectorized_engine import VectorizedBacktester
        
        backtester = VectorizedBacktester()
        result = await backtester.backtest_signals(signals, self.name)
        
        logger.info(f"Backtest completed for {self.name}")
        return result
    
    def is_initialized(self) -> bool:
        """检查策略是否已初始化"""
        return self._initialized

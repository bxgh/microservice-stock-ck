"""策略抽象基类

本模块定义了所有量化策略必须继承的抽象基类。
提供策略生命周期管理、数据处理接口和信号验证功能。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio
import logging

from .signal import Signal

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from adapters.stock_data_provider import StockDataProvider

logger = logging.getLogger(__name__)


class StrategyInitializationError(Exception):
    """策略初始化异常"""
    pass


class BaseStrategy(ABC):
    """策略抽象基类
    
    所有量化策略必须继承此类并实现抽象方法。
    基类提供：
    - 生命周期管理（initialize → 运行 → close）
    - 数据处理接口（on_bar, on_tick）
    - 信号生成和验证
    - 并发安全保护
    
    Attributes:
        strategy_id: 策略唯一标识符
        config: 策略配置参数字典
        data_provider: 数据提供者实例（用于获取历史/实时数据）
        
    Example:
        >>> class MyStrategy(BaseStrategy):
        ...     async def _do_initialize(self):
        ...         # 加载历史数据
        ...         pass
        ...     
        ...     async def on_bar(self, bar_data):
        ...         # 处理K线数据
        ...         pass
        ...     
        ...     def generate_signal(self):
        ...         # 生成信号
        ...         return Signal(...)
    """
    
    def __init__(
        self,
        strategy_id: str,
        config: Dict[str, Any],
        data_provider: 'StockDataProvider' 
    ):
        """初始化策略实例
        
        Args:
            strategy_id: 策略唯一标识符，建议格式: {策略类型}_{版本}_{实例号}
            config: 策略配置参数，如回看窗口、阈值等
            data_provider: 数据提供者实例，用于获取市场数据
        """
        self.strategy_id = strategy_id
        self.config = config
        self.data_provider = data_provider
        self._initialized = False
        self._lock = asyncio.Lock()
        
        logger.info(f"Strategy {strategy_id} instance created")
    
    async def initialize(self) -> None:
        """初始化策略资源（幂等操作）
        
        此方法在策略开始运行前调用，用于：
        - 加载历史数据
        - 初始化模型参数
        - 建立数据连接
        - 验证配置
        
        该方法是幂等的，多次调用只会执行一次初始化。
        使用asyncio.Lock保证并发安全。
        
        Raises:
            StrategyInitializationError: 初始化失败
        """
        async with self._lock:
            if self._initialized:
                logger.debug(f"Strategy {self.strategy_id} already initialized")
                return
            
            try:
                logger.info(f"Initializing strategy {self.strategy_id}...")
                await self._do_initialize()
                self._initialized = True
                logger.info(f"Strategy {self.strategy_id} initialized successfully")
            except Exception as e:
                logger.error(f"Strategy {self.strategy_id} initialization failed: {e}")
                raise StrategyInitializationError(
                    f"Failed to initialize strategy {self.strategy_id}: {e}"
                ) from e
    
    @abstractmethod
    async def _do_initialize(self) -> None:
        """子类实现具体初始化逻辑
        
        在此方法中实现策略特定的初始化代码：
        - 加载历史数据用于计算指标
        - 初始化技术指标状态
        - 加载模型权重
        
        Raises:
            Exception: 初始化过程中的任何异常
        """
        pass
    
    @abstractmethod
    async def on_bar(self, bar_data: Dict[str, Any]) -> None:
        """处理K线数据
        
        当新的K线数据到达时调用此方法。
        子类应在此方法中：
        - 更新技术指标
        - 更新策略状态
        - 判断是否满足信号条件
        
        Args:
            bar_data: K线数据字典，包含以下字段:
                - stock_code (str): 股票代码
                - open (float): 开盘价
                - high (float): 最高价
                - low (float): 最低价
                - close (float): 收盘价
                - volume (int): 成交量
                - amount (float): 成交额
                - timestamp (datetime): 时间戳
        """
        pass
    
    @abstractmethod
    async def on_tick(self, tick_data: Dict[str, Any]) -> None:
        """处理Tick数据
        
        当新的Tick数据到达时调用此方法。
        适用于高频策略或需要逐笔数据的场景。
        
        Args:
            tick_data: Tick数据字典，包含以下字段:
                - stock_code (str): 股票代码
                - price (float): 最新价
                - volume (int): 成交量
                - amount (float): 成交额
                - bid_prices (list): 买盘价格列表（5档）
                - bid_volumes (list): 买盘量列表（5档）
                - ask_prices (list): 卖盘价格列表（5档）
                - ask_volumes (list): 卖盘量列表（5档）
                - timestamp (datetime): 时间戳
        """
        pass
    
    @abstractmethod
    def generate_signal(self) -> Optional[Signal]:
        """生成交易信号
        
        基于当前策略状态生成交易信号。
        此方法应该是纯计算，不应有副作用。
        
        设计为同步方法以减少async开销，
        复杂计算应在on_bar/on_tick中完成。
        
        Returns:
            Signal对象，如果无信号则返回None
        """
        pass
    
    def validate_signal(self, signal: Signal) -> bool:
        """验证信号有效性
        
        对生成的信号进行基础验证。
        子类可以重写此方法添加自定义验证逻辑。
        
        Args:
            signal: 待验证的信号
            
        Returns:
            True表示信号有效，False表示无效
        """
        if not signal:
            return False
        
        # 验证必需字段
        if not signal.stock_code or not signal.direction:
            logger.warning(f"Signal missing required fields: {signal}")
            return False
        
        # 验证信号强度范围
        if signal.strength < 0 or signal.strength > 1:
            logger.warning(f"Signal strength out of range [0,1]: {signal.strength}")
            return False
        
        # 验证交易方向
        if signal.direction not in ["BUY", "SELL", "HOLD"]:
            logger.warning(f"Invalid signal direction: {signal.direction}")
            return False
        
        # 验证目标价格
        if signal.price <= 0:
            logger.warning(f"Invalid signal price: {signal.price}")
            return False
        
        return True
    
    async def close(self) -> None:
        """清理策略资源（幂等操作）
        
        在策略停止运行时调用，用于：
        - 保存策略状态
        - 关闭数据连接
        - 释放内存资源
        
        该方法是幂等的，多次调用只会执行一次清理。
        使用asyncio.Lock保证并发安全。
        即使清理失败也会更新状态标志。
        """
        async with self._lock:
            if not self._initialized:
                logger.debug(f"Strategy {self.strategy_id} not initialized, skip close")
                return
            
            try:
                logger.info(f"Closing strategy {self.strategy_id}...")
                await self._do_close()
                logger.info(f"Strategy {self.strategy_id} closed successfully")
            except Exception as e:
                logger.error(f"Strategy {self.strategy_id} close failed: {e}")
                # 不抛出异常，确保状态被更新
            finally:
                self._initialized = False
    
    @abstractmethod
    async def _do_close(self) -> None:
        """子类实现具体清理逻辑
        
        在此方法中实现策略特定的清理代码：
        - 保存当前状态到数据库
        - 关闭打开的文件或网络连接
        - 释放大型数据结构
        
        Raises:
            Exception: 清理过程中的任何异常
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """检查策略是否已初始化
        
        Returns:
            True表示已初始化，False表示未初始化
        """
        return self._initialized

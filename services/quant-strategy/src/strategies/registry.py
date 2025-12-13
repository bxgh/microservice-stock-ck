"""策略注册表

本模块提供全局策略注册表，管理所有策略实例的生命周期。
使用单例模式确保全局唯一，使用asyncio.Lock保证并发安全。
"""

from typing import Dict, List, Optional
import asyncio
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """策略注册表（单例模式）
    
    管理所有策略实例的注册、查询、启动和停止。
    支持并发安全访问，适用于多协程环境。
    
    设计模式：
    - 单例模式：全局唯一实例
    - 注册表模式：集中管理策略实例
    
    并发安全：
    - 写操作（register/unregister）使用Lock保护
    - 读操作（get/list_all）不加锁，允许脏读
    
    Example:
        >>> registry = StrategyRegistry()
        >>> await registry.register("macd_001", macd_strategy)
        >>> strategy = registry.get("macd_001")
        >>> all_ids = registry.list_all()
        >>> await registry.stop_all()
    """
    
    _instance: Optional['StrategyRegistry'] = None
    _lock_singleton = asyncio.Lock()
    
    def __new__(cls) -> 'StrategyRegistry':
        """确保单例模式
        
        Returns:
            StrategyRegistry的唯一实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化注册表（只执行一次）"""
        # 避免重复初始化
        if not hasattr(self, '_initialized'):
            self._strategies: Dict[str, BaseStrategy] = {}
            self._lock: Optional[asyncio.Lock] = None
            self._initialized = True
            logger.info("StrategyRegistry initialized")
    
    def _ensure_lock(self) -> asyncio.Lock:
        """确保Lock绑定到当前event loop
        
        解决单例模式下Lock跨event loop使用的问题。
        """
        try:
            # 尝试使用现有lock
            if self._lock is not None:
                # 测试是否绑定正确的loop
                loop = asyncio.get_running_loop()
                if self._lock._loop is loop:
                    return self._lock
        except RuntimeError:
            pass
        
        # 创建新lock
        self._lock = asyncio.Lock()
        return self._lock
    
    async def register(
        self,
        strategy_id: str,
        strategy: BaseStrategy
    ) -> None:
        """注册策略到注册表
        
        注册后会自动调用策略的initialize()方法。
        如果策略ID已存在，则抛出异常。
        
        Args:
            strategy_id: 策略唯一标识符
            strategy: 策略实例
            
        Raises:
            ValueError: 策略ID已存在
            Exception: 策略初始化失败
        """
        lock = self._ensure_lock()
        async with lock:
            if strategy_id in self._strategies:
                raise ValueError(
                    f"Strategy '{strategy_id}' already registered"
                )
            
            try:
                # 注册前先初始化
                logger.info(f"Registering strategy '{strategy_id}'...")
                await strategy.initialize()
                self._strategies[strategy_id] = strategy
                logger.info(
                    f"Strategy '{strategy_id}' registered successfully. "
                    f"Total strategies: {len(self._strategies)}"
                )
            except Exception as e:
                logger.error(f"Failed to register strategy '{strategy_id}': {e}")
                raise
    
    async def unregister(self, strategy_id: str) -> None:
        """从注册表注销策略
        
        注销前会自动调用策略的close()方法。
        如果策略不存在，静默返回。
        
        Args:
            strategy_id: 策略标识符
        """
        lock = self._ensure_lock()
        async with lock:
            if strategy_id not in self._strategies:
                logger.warning(f"Strategy '{strategy_id}' not found, skip unregister")
                return
            
            try:
                strategy = self._strategies.pop(strategy_id)
                logger.info(f"Unregistering strategy '{strategy_id}'...")
                await strategy.close()
                logger.info(
                    f"Strategy '{strategy_id}' unregistered. "
                    f"Remaining strategies: {len(self._strategies)}"
                )
            except Exception as e:
                logger.error(f"Failed to unregister strategy '{strategy_id}': {e}")
                # 策略已从字典中移除，即使close失败也继续
    
    def get(self, strategy_id: str) -> Optional[BaseStrategy]:
        """获取指定策略实例（非阻塞）
        
        此方法不加锁，允许读取过程中的脏读，
        以换取更高的查询性能（< 1ms）。
        
        Args:
            strategy_id: 策略标识符
            
        Returns:
            策略实例，如果不存在则返回None
        """
        return self._strategies.get(strategy_id)
    
    def list_all(self) -> List[str]:
        """列出所有已注册的策略ID（非阻塞）
        
        此方法不加锁，返回当前时刻的策略ID列表。
        
        Returns:
            策略ID列表
        """
        return list(self._strategies.keys())
    
    def count(self) -> int:
        """获取已注册策略数量
        
        Returns:
            策略数量
        """
        return len(self._strategies)
    
    async def start_all(self) -> None:
        """启动所有策略
        
        并发初始化所有策略。
        如果部分策略初始化失败，其他策略不受影响。
        
        Returns:
            None，失败的策略会记录错误日志
        """
        if not self._strategies:
            logger.info("No strategies to start")
            return
        
        logger.info(f"Starting all strategies ({len(self._strategies)} in total)...")
        
        tasks = [
            strategy.initialize()
            for strategy in self._strategies.values()
        ]
        
        # return_exceptions=True 确保一个失败不影响其他
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        fail_count = len(results) - success_count
        
        logger.info(
            f"All strategies started. "
            f"Success: {success_count}, Failed: {fail_count}"
        )
        
        # 记录失败的策略
        for strategy_id, result in zip(self._strategies.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Strategy '{strategy_id}' start failed: {result}")
    
    async def stop_all(self) -> None:
        """停止所有策略并清空注册表
        
        并发关闭所有策略，然后清空注册表。
        即使部分策略关闭失败，注册表也会被清空。
        """
        if not self._strategies:
            logger.info("No strategies to stop")
            return
        
        logger.info(f"Stopping all strategies ({len(self._strategies)} in total)...")
        
        tasks = [
            strategy.close()
            for strategy in self._strategies.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        fail_count = len(results) - success_count
        
        logger.info(
            f"All strategies stopped. "
            f"Success: {success_count}, Failed: {fail_count}"
        )
        
        # 记录失败的策略
        for strategy_id, result in zip(list(self._strategies.keys()), results):
            if isinstance(result, Exception):
                logger.error(f"Strategy '{strategy_id}' stop failed: {result}")
        
        # 清空注册表
        lock = self._ensure_lock()
        async with lock:
            self._strategies.clear()
            logger.info("StrategyRegistry cleared")

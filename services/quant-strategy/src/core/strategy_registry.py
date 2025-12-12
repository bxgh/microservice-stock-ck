"""
StrategyRegistry 策略注册表

管理所有策略的注册、查询和实例化
"""
import asyncio
import logging
from typing import Dict, Type, Optional, List
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    策略注册表
    
    使用装饰器自动注册策略类，提供线程安全的注册和查询
    """
    
    _instance: Optional['StrategyRegistry'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._registry_lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls) -> 'StrategyRegistry':
        """获取单例实例 (线程安全)"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                logger.info("StrategyRegistry instance created")
            return cls._instance
    
    async def register(self, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """
        注册策略
        
        Args:
            name: 策略名称
            strategy_class: 策略类
        """
        async with self._registry_lock:
            if name in self._strategies:
                logger.warning(f"Strategy {name} already registered, overwriting")
            
            self._strategies[name] = strategy_class
            logger.info(f"Strategy registered: {name} -> {strategy_class.__name__}")
    
    async def get(self, name: str) -> Optional[Type[BaseStrategy]]:
        """
        获取策略类
        
        Args:
            name: 策略名称
            
        Returns:
            策略类或None
        """
        async with self._registry_lock:
            return self._strategies.get(name)
    
    async def list_strategies(self) -> List[str]:
        """
        列出所有已注册策略
        
        Returns:
            策略名称列表
        """
        async with self._registry_lock:
            return list(self._strategies.keys())
    
    async def create_instance(
        self,
        name: str,
        instance_name: Optional[str] = None,
        parameters: Optional[Dict] = None
    ) -> Optional[BaseStrategy]:
        """
        创建策略实例
        
        Args:
            name: 策略类名称
            instance_name: 实例名称 (默认与类名相同)
            parameters: 策略参数
            
        Returns:
            策略实例或None
        """
        strategy_class = await self.get(name)
        if strategy_class is None:
            logger.error(f"Strategy {name} not found in registry")
            return None
        
        instance_name = instance_name or name
        instance = strategy_class(instance_name, parameters)
        logger.info(f"Strategy instance created: {instance_name}")
        return instance


# 简化的策略注册字典 (避免复杂的异步逻辑)
_STRATEGY_CLASSES: Dict[str, Type[BaseStrategy]] = {}


async def get_registry() -> StrategyRegistry:
    """获取全局注册表实例"""
    registry = await StrategyRegistry.get_instance()
    
    # 将预注册的策略添加到注册表
    async with registry._registry_lock:
        for name, cls in _STRATEGY_CLASSES.items():
            if name not in registry._strategies:
                registry._strategies[name] = cls
                logger.info(f"Strategy auto-registered: {name}")
    
    return registry


def strategy(name: str):
    """
    策略注册装饰器 (简化版)
    
    使用方法:
        @strategy("MyStrategy")
        class MyStrategy(BaseStrategy):
            ...
    
    注意: 实际注册发生在首次调用get_registry()时
    """
    def decorator(cls: Type[BaseStrategy]):
        # 简单地将类存储到字典中
        _STRATEGY_CLASSES[name] = cls
        logger.debug(f"Strategy class marked for registration: {name}")
        return cls
    
    return decorator

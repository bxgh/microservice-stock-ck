from typing import Dict, Type, Optional, List
import logging
from .base import BaseStrategy

logger = logging.getLogger(__name__)

class StrategyRegistry:
    """
    策略注册中心
    
    负责管理所有策略类的注册、实例化和获取。
    """
    
    _registry: Dict[str, Type[BaseStrategy]] = {}
    _instances: Dict[str, BaseStrategy] = {}
    
    @classmethod
    def register(cls, strategy_class: Type[BaseStrategy]):
        """
        注册策略类 (Decorator)
        """
        name = strategy_class.__name__
        cls._registry[name] = strategy_class
        logger.info(f"Registered strategy class: {name}")
        return strategy_class

    @classmethod
    def create_strategy(cls, strategy_name: str, config: dict = None) -> Optional[BaseStrategy]:
        """
        创建策略实例
        """
        if strategy_name not in cls._registry:
            logger.error(f"Strategy class {strategy_name} not found")
            return None
            
        strategy_class = cls._registry[strategy_name]
        try:
            instance = strategy_class(name=strategy_name, config=config)
            cls._instances[strategy_name] = instance
            logger.info(f"Created strategy instance: {strategy_name}")
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate strategy {strategy_name}: {e}")
            return None

    @classmethod
    def get_strategy(cls, strategy_name: str) -> Optional[BaseStrategy]:
        """获取已实例化的策略"""
        return cls._instances.get(strategy_name)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """列出所有支持的策略名称"""
        return list(cls._registry.keys())

    @classmethod
    def list_active_strategies(cls) -> List[str]:
        """列出正在运行的策略"""
        return list(cls._instances.keys())

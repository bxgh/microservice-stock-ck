"""
风险控制核心模块

定义风控管理器和规则基类。
采用拦截过滤器模式 (Intercepting Filter Pattern)。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

# 避免循环引用，只在类型检查时导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from strategies.signal import Signal

logger = logging.getLogger(__name__)

class RiskRule(ABC):
    """风控规则基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """规则名称"""
        pass
        
    @abstractmethod
    async def check(self, signal: 'Signal', context: Dict[str, Any] = None) -> bool:
        """
        执行风控检查
        
        Args:
            signal: 交易信号对象
            context: 上下文信息 (如当前持仓、资金等)
            
        Returns:
            bool: True表示通过，False表示拒绝
        """
        pass

class RiskManager:
    """风控管理器 (单例)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rules = []
            cls._instance._lock = asyncio.Lock()
        return cls._instance
    
    def __init__(self):
        # 初始化逻辑在 __new__ 中完成，避免重复初始化
        pass
        
    def add_rule(self, rule: RiskRule):
        """添加风控规则"""
        self._rules.append(rule)
        logger.info(f"Added risk rule: {rule.name}")
        
    def clear_rules(self):
        """清空所有规则"""
        self._rules = []
        logger.info("Cleared all risk rules")
        
    async def validate(self, signal: 'Signal', context: Dict[str, Any] = None) -> bool:
        """
        验证信号是否符合所有风控规则
        
        Args:
            signal: 交易信号
            context: 上下文 (可选)
            
        Returns:
            bool: True表示通过所有规则，False表示被拦截
        """
        if not self._rules:
            return True
            
        context = context or {}
        
        for rule in self._rules:
            try:
                passed = await rule.check(signal, context)
                if not passed:
                    logger.warning(f"Signal rejected by risk rule: {rule.name} | Signal: {signal}")
                    return False
            except Exception as e:
                logger.error(f"Error executing risk rule {rule.name}: {e}", exc_info=True)
                # 默认策略：风控执行出错时，为了安全起见，通常选择拒绝？
                # 或者选择放行并报警？这里选择拒绝 (Fail Safe)
                logger.warning(f"Signal rejected due to risk rule error: {rule.name}")
                return False
                
        return True

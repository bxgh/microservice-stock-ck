"""
重试策略实现

为任务执行提供重试机制，支持指数退避策略
"""

import logging
import asyncio
from typing import Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    backoff_seconds: int = 60
    backoff_multiplier: float = 2.0


class RetryPolicy:
    """重试策略"""
    
    def __init__(self, config: RetryConfig):
        """
        初始化重试策略
        
        Args:
            config: 重试配置
        """
        self.config = config
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        使用重试策略执行函数
        
        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次执行的异常
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.info(
                    f"🔄 Attempt {attempt}/{self.config.max_attempts}"
                )
                
                # 执行函数
                result = await func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info(
                        f"✓ Succeeded on attempt {attempt}"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 如果是最后一次尝试，直接抛出异常
                if attempt == self.config.max_attempts:
                    logger.error(
                        f"❌ All {self.config.max_attempts} attempts failed"
                    )
                    raise
                
                # 计算退避时间
                wait_time = self._calculate_backoff(attempt)
                
                logger.warning(
                    f"⚠️ Attempt {attempt} failed: {str(e)[:100]}, "
                    f"retrying in {wait_time}s..."
                )
                
                # 等待后重试
                await asyncio.sleep(wait_time)
        
        # 不应该到达这里，但为了类型安全
        raise last_exception or RuntimeError("Retry failed without exception")
    
    def _calculate_backoff(self, attempt: int) -> float:
        """
        计算指数退避时间
        
        Args:
            attempt: 当前尝试次数
            
        Returns:
            等待时间(秒)
        """
        return self.config.backoff_seconds * (
            self.config.backoff_multiplier ** (attempt - 1)
        )

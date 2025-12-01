import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


class RetryPolicy:
    """
    重试策略
    
    实现指数退避重试算法，用于处理临时性故障。
    """
    
    def __init__(self,
                 max_retries: int = 5,
                 base_delay: float = 1.0):
        """
        初始化重试策略
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒），实际延迟 = base_delay * (2 ** attempt)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.total_retries = 0
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数，失败时自动重试
        
        Args:
            func: 要执行的异步函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次失败的异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"✅ Retry succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt >= self.max_retries:
                    logger.error(f"❌ Failed after {self.max_retries + 1} attempts: {e}")
                    raise
                
                # 计算退避时间（指数退避）
                wait_time = self._calculate_backoff(attempt)
                logger.warning(
                    f"⚠️ Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                
                await asyncio.sleep(wait_time)
                self.total_retries += 1
        
        # 理论上不会到达这里，但为了类型安全
        raise last_exception
    
    def _calculate_backoff(self, attempt: int) -> float:
        """
        计算指数退避时间
        
        Args:
            attempt: 当前尝试次数（从0开始）
            
        Returns:
            延迟时间（秒）
            
        Examples:
            attempt 0: 1s
            attempt 1: 2s
            attempt 2: 4s
            attempt 3: 8s
            attempt 4: 16s
        """
        return self.base_delay * (2 ** attempt)
    
    def get_stats(self) -> dict:
        """获取重试统计"""
        return {
            'max_retries': self.max_retries,
            'total_retries': self.total_retries
        }

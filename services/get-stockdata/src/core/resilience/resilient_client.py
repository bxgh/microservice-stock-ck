from typing import Callable, Any
import logging
from .circuit_breaker import CircuitBreaker, CircuitState
from .retry_policy import RetryPolicy

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """断路器开启时抛出的异常"""
    pass


class MaxRetriesExceededError(Exception):
    """重试次数耗尽时抛出的异常"""
    pass


class ResilientClient:
    """
    弹性客户端包装器
    
    为任何异步函数提供重试和熔断能力，确保系统在面对不稳定服务时的健壮性。
    
    Example:
        >>> resilient = ResilientClient(max_retries=3, base_delay=1.0)
        >>> 
        >>> async def unstable_api():
        >>>     # 可能失败的API调用
        >>>     return await some_external_service()
        >>> 
        >>> result = await resilient.execute(unstable_api)
    """
    
    def __init__(self,
                 max_retries: int = 5,
                 base_delay: float = 1.0,
                 failure_threshold: int = 5,
                 circuit_timeout: int = 600):
        """
        初始化弹性客户端
        
        Args:
            max_retries: 最大重试次数
            base_delay: 重试基础延迟（秒）
            failure_threshold: 触发熔断的连续失败次数
            circuit_timeout: 熔断后等待恢复的时间（秒）
        """
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            timeout=circuit_timeout
        )
        self.retry_policy = RetryPolicy(
            max_retries=max_retries,
            base_delay=base_delay
        )
        
        # 统计信息
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'circuit_opens': 0
        }
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数，带重试和熔断保护
        
        Args:
            func: 要执行的异步函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitBreakerOpenError: 断路器开启时
            MaxRetriesExceededError: 重试次数耗尽时
        """
        self.stats['total_calls'] += 1
        
        # 1. 检查断路器状态
        if not self.circuit_breaker.can_execute():
            self.stats['failed_calls'] += 1
            raise CircuitBreakerOpenError(
                f"Circuit breaker is {self.circuit_breaker.state.value}. "
                f"Service temporarily unavailable."
            )
        
        # 2. 执行带重试的调用
        try:
            result = await self.retry_policy.execute(func, *args, **kwargs)
            
            # 成功
            self.circuit_breaker.record_success()
            self.stats['successful_calls'] += 1
            return result
            
        except Exception as e:
            # 失败
            self.circuit_breaker.record_failure()
            self.stats['failed_calls'] += 1
            
            # 检查是否触发了熔断
            if self.circuit_breaker.state == CircuitState.OPEN:
                prev_opens = self.stats['circuit_opens']
                self.stats['circuit_opens'] = prev_opens + 1
                logger.error(
                    f"🚨 Circuit breaker opened (total: {self.stats['circuit_opens']}). "
                    f"Failing fast for {self.circuit_breaker.timeout}s."
                )
            
            raise MaxRetriesExceededError(
                f"Failed after {self.retry_policy.max_retries + 1} attempts: {e}"
            ) from e
    
    def get_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            包含调用统计和成功率的字典
        """
        total = self.stats['total_calls']
        if total == 0:
            success_rate = 100.0
        else:
            success_rate = (self.stats['successful_calls'] / total) * 100
        
        return {
            **self.stats,
            'success_rate': f"{success_rate:.2f}%",
            'circuit_state': self.circuit_breaker.state.value,
            'total_retries': self.retry_policy.total_retries
        }
    
    def reset(self):
        """重置统计信息（用于测试或重新开始统计）"""
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'circuit_opens': 0
        }
        self.circuit_breaker._close()
        self.retry_policy.total_retries = 0

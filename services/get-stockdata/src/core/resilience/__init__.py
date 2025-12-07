"""
弹性机制核心组件

提供重试、熔断等容错能力，用于包装不稳定的外部调用。
"""

from .circuit_breaker import CircuitBreaker, CircuitState
from .retry_policy import RetryPolicy
from .resilient_client import ResilientClient, CircuitBreakerOpenError, MaxRetriesExceededError

__all__ = [
    'CircuitBreaker',
    'CircuitState',
    'RetryPolicy',
    'ResilientClient',
    'CircuitBreakerOpenError',
    'MaxRetriesExceededError',
]

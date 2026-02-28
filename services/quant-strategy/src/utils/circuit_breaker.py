import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

class CircuitBreakerOpenError(Exception):
    """当策略触发熔断时抛出此异常，终止本次运算投喂"""
    pass

class TickClusterCircuitBreaker:
    """
    保护 Quant 模型计算崩溃的极端熔断器。

    1. 当计算单元遇到报错/阻塞超时达到阈值，将阻断下一次调用。
    2. 等待 Recovery 时间后尝试放出少量调用的 Half-Open 状态。
    """
    def __init__(
        self,
        failure_threshold: int = 3,
        timeout_sec: int = 300,  # 单步 5 分钟死锁容忍
        recovery_sec: int = 600  # 冷却 10 分钟重试
    ):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout_sec
        self.recovery_timeout = recovery_sec

        self.state = 'CLOSED'  # CLOSED (正常计算) / OPEN (切断运算) / HALF_OPEN (放出测试)
        self.last_failure_time = 0.0

    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """]
        尝试执行异步方法，如果有熔断则直接弹回。
        """
        # 1. 拦截评估
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                logger.warning("Circuit breaker entering HALF_OPEN state. Attempting recovery.")
            else:
                logger.error("Circuit breaker is OPEN. Strategy generation blocked.")
                raise CircuitBreakerOpenError("熔断器阻断，系统处于不稳定/极端危险行情中。")

        # 2. 调用监控
        try:
            # 引入超时拦截
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )

            # 如果是 HALF_OPEN 或者之前有错误，健康康复
            if self.failure_count > 0:
                self.failure_count = 0
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                logger.info("Circuit breaker RECOVERED to CLOSED state.")

            return result

        except TimeoutError:
            self.failure_count += 1
            self.last_failure_time = time.time()
            logger.error(f"Execution TIMEOUT ({self.timeout}s). Failure Count: {self.failure_count}")
            self._check_trip()
            raise

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            logger.error(f"Execution FAILED: {str(e)}. Failure Count: {self.failure_count}")
            self._check_trip()
            raise

    def execute_sync(self, func: Callable, *args, **kwargs) -> Any:
        """针对非异步执行的统一包装"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                logger.warning("Circuit breaker entering HALF_OPEN state. Attempting recovery.")
            else:
                logger.error("Circuit breaker is OPEN. Strategy generation blocked.")
                raise CircuitBreakerOpenError("熔断器阻断，系统处于不稳定/极端危险行情中。")

        # Warning: Sync does not support native async.wait_for timeout interruption.
        # Only catching exceptions.
        try:
            result = func(*args, **kwargs)

            if self.failure_count > 0:
                self.failure_count = 0
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                logger.info("Circuit breaker RECOVERED to CLOSED state.")

            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            logger.error(f"Execution FAILED: {str(e)}. Failure Count: {self.failure_count}")
            self._check_trip()
            raise

    def manual_trip(self):
        """支持针对超极端外部行情(大盘崩盘)的主动拨断"""
        self.state = 'OPEN'
        self.last_failure_time = time.time()
        logger.critical("Circuit breaker MANUALLY TRIPPED (e.g. Extreme market protection!).")

    def _check_trip(self):
        if self.failure_count >= self.failure_threshold and self.state != 'OPEN':
            self.state = 'OPEN'
            logger.critical(f"Circuit breaker TRIPPED to OPEN state! More than {self.failure_threshold} consecutive errors.")

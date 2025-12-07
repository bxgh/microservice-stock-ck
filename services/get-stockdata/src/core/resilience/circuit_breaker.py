from enum import Enum
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """断路器状态"""
    CLOSED = "CLOSED"       # 正常状态
    OPEN = "OPEN"           # 熔断状态
    HALF_OPEN = "HALF_OPEN" # 半开状态


class CircuitBreaker:
    """
    断路器实现
    
    自动检测连续失败并触发熔断，保护系统免受级联故障。
    
    状态转换:
    CLOSED --[连续失败≥阈值]--> OPEN --[超时]--> HALF_OPEN --[成功]--> CLOSED
                                           |                    |
                                           +-----[失败]----------+
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 timeout: int = 600):
        """
        初始化断路器
        
        Args:
            failure_threshold: 触发熔断的连续失败次数
            timeout: 熔断后等待恢复的时间（秒）
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count_in_half_open = 0
        
    def record_success(self):
        """记录成功调用"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count_in_half_open += 1
            # 半开状态连续成功2次，关闭断路器
            if self.success_count_in_half_open >= 2:
                logger.info("Circuit breaker CLOSED after successful recovery")
                self._close()
        elif self.state == CircuitState.CLOSED:
            # 正常状态下成功，重置失败计数
            self.failure_count = 0
    
    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # 半开状态失败，重新打开断路器
            logger.warning("Circuit breaker re-OPENED after failure in HALF_OPEN state")
            self._open()
        elif self.failure_count >= self.failure_threshold:
            # 连续失败达到阈值，打开断路器
            logger.error(f"Circuit breaker OPENED after {self.failure_count} consecutive failures")
            self._open()
    
    def can_execute(self) -> bool:
        """
        判断是否允许执行调用
        
        Returns:
            bool: True 允许执行，False 拒绝执行（熔断中）
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # 检查是否超时，可以尝试恢复
            if self._should_attempt_reset():
                logger.info("Circuit breaker entering HALF_OPEN state")
                self._half_open()
                return True
            return False
        
        # HALF_OPEN 状态允许执行
        return True
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置断路器"""
        if self.last_failure_time is None:
            return True
        
        elapsed = datetime.now() - self.last_failure_time
        return elapsed.total_seconds() >= self.timeout
    
    def _close(self):
        """关闭断路器（恢复正常）"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count_in_half_open = 0
    
    def _open(self):
        """打开断路器（进入熔断）"""
        self.state = CircuitState.OPEN
        self.success_count_in_half_open = 0
    
    def _half_open(self):
        """设置为半开状态"""
        self.state = CircuitState.HALF_OPEN
        self.success_count_in_half_open = 0

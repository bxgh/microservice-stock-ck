# -*- coding: utf-8 -*-
"""
gRPC 熔断器实现

针对 gRPC 调用的熔断器，支持：
- 基于错误码的熔断判断
- 半开/开/关状态机
- 自动恢复机制
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import grpc

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"          # 正常状态
    OPEN = "open"              # 熔断状态
    HALF_OPEN = "half_open"    # 半开状态


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5           # 失败阈值
    success_threshold: int = 2           # 半开状态下的成功阈值
    recovery_timeout: float = 60.0       # 熔断恢复时间(秒)
    
    # gRPC 错误码配置
    fatal_status_codes: tuple = (
        grpc.StatusCode.UNAVAILABLE,
        grpc.StatusCode.DEADLINE_EXCEEDED,
        grpc.StatusCode.RESOURCE_EXHAUSTED,
    )


class GrpcCircuitBreaker:
    """gRPC 熔断器
    
    特点：
    - 针对 gRPC 错误码进行熔断判断
    - 支持三态切换：CLOSED -> OPEN -> HALF_OPEN -> CLOSED
    - 自动恢复机制
    
    Example:
        cb = GrpcCircuitBreaker("mootdx-source")
        
        try:
            if cb.is_open():
                raise Exception("Circuit is open")
            
            response = await grpc_client.FetchData(request)
            cb.record_success()
        except grpc.RpcError as e:
            cb.record_failure(e.code())
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """初始化熔断器
        
        Args:
            name: 熔断器名称（通常为服务名）
            config: 熔断器配置
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0  # 半开状态下的成功计数
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: Optional[datetime] = None
        
        logger.info(
            f"Circuit breaker initialized for {name}: "
            f"threshold={self.config.failure_threshold}, "
            f"recovery={self.config.recovery_timeout}s"
        )
    
    def is_open(self) -> bool:
        """检查熔断器是否打开
        
        Returns:
            bool: True 表示熔断器打开，应拒绝请求
        """
        if self.state == CircuitState.CLOSED:
            return False
        
        if self.state == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} entering half-open state")
                    return False
            return True
        
        # HALF_OPEN 状态允许请求通过
        return False
    
    def record_success(self) -> None:
        """记录成功调用"""
        if self.state == CircuitState.CLOSED:
            self.failure_count = 0
        
        elif self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} recovered to closed state")
    
    def record_failure(self, status_code: Optional[grpc.StatusCode] = None) -> None:
        """记录失败调用
        
        Args:
            status_code: gRPC 错误码
        """
        # 检查是否为致命错误码
        if status_code and status_code not in self.config.fatal_status_codes:
            # 非致命错误不计入熔断
            logger.debug(f"Non-fatal error {status_code} for {self.name}, not counted")
            return
        
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # 半开状态下失败，立即回到熔断状态
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                f"Circuit breaker {self.name} reopened from half-open state "
                f"(status_code={status_code})"
            )
        
        elif self.failure_count >= self.config.failure_threshold:
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                f"Circuit breaker {self.name} opened after {self.failure_count} failures "
                f"(status_code={status_code})"
            )
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """状态转换"""
        old_state = self.state
        self.state = new_state
        self.last_state_change = datetime.now()
        logger.info(f"Circuit breaker {self.name}: {old_state} -> {new_state}")
    
    def get_state(self) -> CircuitState:
        """获取当前状态"""
        return self.state
    
    def reset(self) -> None:
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker {self.name} reset")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat() if self.last_state_change else None,
        }
    
    def __repr__(self) -> str:
        return f"<GrpcCircuitBreaker({self.name}, state={self.state.value}, failures={self.failure_count})>"

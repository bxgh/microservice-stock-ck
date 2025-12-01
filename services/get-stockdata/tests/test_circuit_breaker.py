import pytest
import time
from datetime import datetime, timedelta
from src.core.resilience.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_initial_state():
    """测试断路器初始状态"""
    cb = CircuitBreaker()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() == True
    assert cb.failure_count == 0


def test_circuit_breaker_opens_after_failures():
    """测试连续失败后断路器打开"""
    cb = CircuitBreaker(failure_threshold=3)
    
    # 记录3次失败
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED  # 还未达到阈值
    
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    
    cb.record_failure()
    assert cb.state == CircuitState.OPEN  # 达到阈值，熔断
    assert cb.can_execute() == False


def test_circuit_breaker_success_resets_failure_count():
    """测试成功调用重置失败计数"""
    cb = CircuitBreaker(failure_threshold=3)
    
    cb.record_failure()
    cb.record_failure()
    assert cb.failure_count == 2
    
    cb.record_success()
    assert cb.failure_count == 0  # 重置


def test_circuit_breaker_half_open_after_timeout():
    """测试超时后进入半开状态"""
    cb = CircuitBreaker(failure_threshold=2, timeout=1)
    
    # 触发熔断
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    
    # 等待超时
    time.sleep(1.1)
    
    # 调用 can_execute 应该自动转为半开
    can_exec = cb.can_execute()
    assert can_exec == True
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_breaker_closes_after_success_in_half_open():
    """测试半开状态连续成功后关闭断路器"""
    cb = CircuitBreaker(failure_threshold=2, timeout=0)
    
    # 触发熔断并手动进入半开
    cb.record_failure()
    cb.record_failure()
    cb._half_open()
    
    assert cb.state == CircuitState.HALF_OPEN
    
    # 第一次成功
    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN  # 还未关闭
    
    # 第二次成功，应该关闭
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_reopens_on_failure_in_half_open():
    """测试半开状态失败后重新打开"""
    cb = CircuitBreaker(failure_threshold=2, timeout=0)
    
    # 触发熔断并手动进入半开
    cb.record_failure()
    cb.record_failure()
    cb._half_open()
    
    assert cb.state == CircuitState.HALF_OPEN
    
    # 半开状态失败，应该重新打开
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_should_attempt_reset():
    """测试超时判断逻辑"""
    cb = CircuitBreaker(failure_threshold=1, timeout=5)
    
    # 无失败时间，应该允许重置
    assert cb._should_attempt_reset() == True
    
    # 设置最近失败时间为现在
    cb.last_failure_time = datetime.now()
    assert cb._should_attempt_reset() == False
    
    # 设置最近失败时间为6秒前
    cb.last_failure_time = datetime.now() - timedelta(seconds=6)
    assert cb._should_attempt_reset() == True

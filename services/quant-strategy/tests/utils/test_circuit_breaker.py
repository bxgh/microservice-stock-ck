"""熔断器逻辑单元测试"""
import pytest

from utils.circuit_breaker import CircuitBreakerOpenError, TickClusterCircuitBreaker


@pytest.mark.asyncio
async def test_circuit_breaker_trips_after_threshold():
    """连续失败达到阈值后，熔断器状态变为 OPEN"""
    breaker = TickClusterCircuitBreaker(failure_threshold=3, timeout_sec=5, recovery_sec=600)

    async def always_fail():
        raise RuntimeError("模拟数据源错误")

    # 连续失败 3 次
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.execute_async(always_fail)

    # 第 4 次应被熔断拦截，而不是抛 RuntimeError
    assert breaker.state == "OPEN"
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.execute_async(always_fail)


@pytest.mark.asyncio
async def test_circuit_breaker_recovers_after_success():
    """触发后若调用成功，熔断器应恢复到 CLOSED 状态"""
    breaker = TickClusterCircuitBreaker(failure_threshold=2, timeout_sec=5, recovery_sec=0)

    async def always_fail():
        raise ValueError("失败")

    # Trip
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.execute_async(always_fail)

    assert breaker.state == "OPEN"

    # 使 recovery_timeout = 0 立刻允许 HALF_OPEN
    breaker.last_failure_time = 0  # 强制使其过期

    async def healthy():
        return "OK"

    result = await breaker.execute_async(healthy)
    assert result == "OK"
    assert breaker.state == "CLOSED"


def test_manual_trip():
    """手动拨断在极端行情下可立即触发"""
    breaker = TickClusterCircuitBreaker()
    assert breaker.state == "CLOSED"

    breaker.manual_trip()
    assert breaker.state == "OPEN"

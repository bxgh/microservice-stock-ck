import pytest
from src.core.resilience.resilient_client import (
    ResilientClient,
    CircuitBreakerOpenError,
    MaxRetriesExceededError
)


@pytest.mark.asyncio
async def test_resilient_client_success_on_first_call():
    """测试首次调用成功"""
    client = ResilientClient(max_retries=3, base_delay=0.1)
    
    async def stable_api():
        return {"data": "success"}
    
    result = await client.execute(stable_api)
    assert result == {"data": "success"}
    
    stats = client.get_stats()
    assert stats['successful_calls'] == 1
    assert stats['failed_calls'] == 0
    assert stats['circuit_state'] == 'CLOSED'


@pytest.mark.asyncio
async def test_resilient_client_with_transient_failure():
    """测试临时性故障后重试成功"""
    client = ResilientClient(max_retries=3, base_delay=0.1)
    
    call_count = 0
    async def unstable_api():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("Network timeout")
        return {"data": "success"}
    
    result = await client.execute(unstable_api)
    assert result == {"data": "success"}
    assert call_count == 3
    
    stats = client.get_stats()
    assert stats['successful_calls'] == 1
    assert stats['failed_calls'] == 0
    assert stats['circuit_state'] == 'CLOSED'


@pytest.mark.asyncio
async def test_resilient_client_fails_after_max_retries():
    """测试重试耗尽后失败"""
    client = ResilientClient(max_retries=2, base_delay=0.1)
    
    async def broken_api():
        raise ConnectionError("Permanent error")
    
    with pytest.raises(MaxRetriesExceededError):
        await client.execute(broken_api)
    
    stats = client.get_stats()
    assert stats['successful_calls'] == 0
    assert stats['failed_calls'] == 1


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_consecutive_failures():
    """测试连续失败后熔断"""
    client = ResilientClient(
        max_retries=0,  # 不重试，快速失败
        failure_threshold=3,
        circuit_timeout=60
    )
    
    async def broken_api():
        raise ConnectionError("Service unavailable")
    
    # 连续失败3次，触发熔断
    for i in range(3):
        try:
            await client.execute(broken_api)
        except MaxRetriesExceededError:
            pass
    
    stats = client.get_stats()
    assert stats['circuit_opens'] == 1
    assert stats['circuit_state'] == 'OPEN'
    
    # 断路器打开后，应该拒绝请求
    with pytest.raises(CircuitBreakerOpenError):
        await client.execute(broken_api)


@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    """测试熔断恢复"""
    client = ResilientClient(
        max_retries=0,
        failure_threshold=2,
        circuit_timeout=1  # 1秒后尝试恢复
    )
    
    call_count = 0
    async def recovering_api():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("Temporarily down")
        return {"status": "recovered"}
    
    # 触发熔断
    for _ in range(2):
        try:
            await client.execute(recovering_api)
        except MaxRetriesExceededError:
            pass
    
    assert client.circuit_breaker.state.value == 'OPEN'
    
    # 等待超时
    import asyncio
    await asyncio.sleep(1.1)
    
    # 应该允许尝试
    result = await client.execute(recovering_api)
    assert result == {"status": "recovered"}
    
    # 成功后断路器应该关闭（需要2次成功）
    await client.execute(recovering_api)
    assert client.circuit_breaker.state.value == 'CLOSED'


@pytest.mark.asyncio
async def test_resilient_client_statistics():
    """测试统计信息准确性"""
    client = ResilientClient(max_retries=2, base_delay=0.05)
    
    # 1次成功
    async def success():
        return "ok"
    await client.execute(success)
    
    # 1次失败（重试耗尽）
    try:
        call_count = 0
        async def fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fail")
        await client.execute(fail)
    except MaxRetriesExceededError:
        pass
    
    stats = client.get_stats()
    assert stats['total_calls'] == 2
    assert stats['successful_calls'] == 1
    assert stats['failed_calls'] == 1
    assert '50.00%' in stats['success_rate']

import pytest
from src.core.resilience.retry_policy import RetryPolicy


@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt():
    """测试首次调用成功"""
    policy = RetryPolicy(max_retries=3)
    
    call_count = 0
    async def func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await policy.execute(func)
    assert result == "success"
    assert call_count == 1  # 只调用一次


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    """测试重试后成功"""
    policy = RetryPolicy(max_retries=3, base_delay=0.1)
    
    call_count = 0
    async def func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"
    
    result = await policy.execute(func)
    assert result == "success"
    assert call_count == 3  # 失败2次，第3次成功


@pytest.mark.asyncio
async def test_retry_fails_after_max_retries():
    """测试重试次数耗尽后失败"""
    policy = RetryPolicy(max_retries=2, base_delay=0.1)
    
    call_count = 0
    async def func():
        nonlocal call_count
        call_count += 1
        raise ValueError("Permanent error")
    
    with pytest.raises(ValueError) as exc_info:
        await policy.execute(func)
    
    assert "Permanent error" in str(exc_info.value)
    assert call_count == 3  # 初次 + 2次重试


@pytest.mark.asyncio
async def test_exponential_backoff():
    """测试指数退避时间计算"""
    policy = RetryPolicy(max_retries=4, base_delay=1.0)
    
    assert policy._calculate_backoff(0) == 1.0   # 2^0 = 1
    assert policy._calculate_backoff(1) == 2.0   # 2^1 = 2
    assert policy._calculate_backoff(2) == 4.0   # 2^2 = 4
    assert policy._calculate_backoff(3) == 8.0   # 2^3 = 8
    assert policy._calculate_backoff(4) == 16.0  # 2^4 = 16


@pytest.mark.asyncio
async def test_retry_statistics():
    """测试重试统计"""
    policy = RetryPolicy(max_retries=3, base_delay=0.05)
    
    call_count = 0
    async def func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Error")
        return "success"
    
    await policy.execute(func)
    
    stats = policy.get_stats()
    assert stats['total_retries'] == 2  # 重试了2次
    assert stats['max_retries'] == 3

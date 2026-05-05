import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.api_client import MySQLDataClient
from src.core.exceptions import DataSourceError, DataSourceEmptyError
import httpx

@pytest.mark.asyncio
async def test_api_client_retry_logic():
    """测试 MySQLDataClient 的重试逻辑"""
    client = MySQLDataClient(base_url="http://test-api")
    
    # 模拟 httpx 请求失败，前两次报错，第三次成功
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"trade_date": "2024-01-01", "close_price": 10.0}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get") as mock_get:
        # 设置副作用：失败, 失败, 成功
        mock_get.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.TimeoutException("Timeout"),
            mock_response
        ]
        
        # 为了缩短测试时间，修改重试等待时间
        with patch("src.data.resilience.stop_after_attempt", return_value=stop_after_attempt_mock(3)):
            # 注意：with_retry 装饰器在定义时已经固定了参数，这里通过 patch 可能会比较复杂
            # 我们直接测试 fetch_kline，看它是否能最终成功
            df = await client.fetch_kline("000001.SZ", "2024-01-01")
            
            assert not df.empty
            assert mock_get.call_count == 3

def stop_after_attempt_mock(n):
    from tenacity import stop_after_attempt
    return stop_after_attempt(n)

@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    """测试断路器开启逻辑"""
    client = MySQLDataClient(base_url="http://test-api")
    client.breaker.failure_threshold = 3  # 调低阈值方便测试
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Persistent failure")
        
        # 连续失败 3 次
        for _ in range(3):
            with pytest.raises(DataSourceError):
                await client.fetch_kline("000001.SZ", "2024-01-01")
        
        # 断路器应该开启
        assert client.breaker.state == "OPEN"
        
        # 第 4 次请求应该直接由于断路器而失败，不调用 httpx
        with pytest.raises(DataSourceError) as excinfo:
            await client.fetch_kline("000001.SZ", "2024-01-01")
        
        assert "Circuit breaker is OPEN" in str(excinfo.value)
        assert mock_get.call_count == 3  # 虽然 fetch_kline 有重试，但在失败 threshold 次后就不该再试了
        # 注意：tenacity 的重试会在单次调用中重试。如果失败了 3 次（单次调用内），断路器会记录 3 次失败吗？
        # 我们的实现中，_request 在每次失败时都会记录。
        # 如果 fetch_kline 重试 3 次，_request 就会被调 3 次，断路器失败计数 +3。

@pytest.mark.asyncio
async def test_api_client_404_handling():
    """测试 404 处理，不应触发断路器失败"""
    client = MySQLDataClient(base_url="http://test-api")
    
    mock_response = MagicMock()
    mock_response.status_code = 404
    
    with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        with pytest.raises(DataSourceEmptyError):
            await client.fetch_kline("UNKNOWN", "2024-01-01")
            
        assert client.breaker.failure_count == 0
        assert client.breaker.state == "CLOSED"

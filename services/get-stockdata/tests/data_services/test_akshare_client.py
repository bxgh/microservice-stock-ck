
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.data_services.akshare_client import AkShareClient, AkShareTimeoutError, CircuitBreakerOpenError

@pytest.mark.asyncio
async def test_akshare_client_success():
    client = AkShareClient()
    
    with patch('akshare.stock_zh_a_spot_em') as mock_func:
        mock_func.return_value = "success"
        
        result = await client.call('stock_zh_a_spot_em')
        assert result == "success"
        assert client._failure_count == 0

@pytest.mark.asyncio
async def test_akshare_client_retry():
    client = AkShareClient(timeout=1, max_retries=2)
    
    with patch('akshare.stock_zh_a_spot_em') as mock_func:
        # Fail twice, then succeed
        mock_func.side_effect = [Exception("Fail 1"), Exception("Fail 2"), "success"]
        
        result = await client.call('stock_zh_a_spot_em')
        assert result == "success"
        assert mock_func.call_count == 3
        assert client._failure_count == 0

@pytest.mark.asyncio
async def test_akshare_client_circuit_breaker():
    client = AkShareClient(timeout=1, max_retries=1)
    client._failure_threshold = 2 # Trigger fast
    
    with patch('akshare.stock_zh_a_spot_em') as mock_func:
        mock_func.side_effect = Exception("Persistent Failure")
        
        # 1. First failure (Attempt 1 + 1 retry = 2 calls)
        try:
            await client.call('stock_zh_a_spot_em')
        except Exception:
            pass
            
        # 2. Second failure
        try:
            await client.call('stock_zh_a_spot_em')
        except Exception:
            pass
            
        assert client._circuit_open == True
        
        # 3. Should raise CircuitBreakerOpenError immediately
        with pytest.raises(CircuitBreakerOpenError):
            await client.call('stock_zh_a_spot_em')
            
    print("✅ Circuit Breaker Test Passed")

if __name__ == "__main__":
    asyncio.run(test_akshare_client_circuit_breaker())

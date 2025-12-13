"""Unit tests for StockDataProvider"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import pandas as pd
import sys
sys.path.insert(0, '/app/src')

from adapters.stock_data_provider import StockDataProvider


class TestStockDataProviderBasic:
    """Basic functionality tests"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test provider initialization"""
        provider = StockDataProvider()
        assert provider.base_url == "http://127.0.0.1:8083"
        await provider.initialize()
        assert provider._session is not None
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_get_quotes_empty(self):
        """Test with empty list"""
        provider = StockDataProvider()
        await provider.initialize()
        df = await provider.get_realtime_quotes([])
        assert len(df) == 0
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_get_quotes_success(self):
        """Test successful quote fetch with mock"""
        provider = StockDataProvider()
        await provider.initialize()
        
        with patch.object(provider, '_make_request', new=AsyncMock(return_value={
            'code': '600519', 'price': 1850.0, 'volume': 150000
        })):
            df = await provider.get_realtime_quotes(['600519'])
            assert len(df) == 1
            assert df.iloc[0]['code'] == '600519'
        
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test API error handling"""
        provider = StockDataProvider()
        await provider.initialize()
        
        with patch.object(provider, '_make_request', new=AsyncMock(side_effect=Exception("API Error"))):
            df = await provider.get_realtime_quotes(['600519'])
            assert len(df) == 0  # Should return empty on error
        
        await provider.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

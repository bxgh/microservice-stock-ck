"""Unit tests for StockDataProvider"""
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, '/home/bxgh/microservice-stock/services/quant-strategy/src')

from adapters.stock_data_provider import StockDataProvider


class TestStockDataProviderBasic:
    """Basic functionality tests"""

    @pytest.fixture(autouse=True)
    def mock_redis(self):
        """Mock redis client to prevent external dependency and state pollution"""
        with patch('adapters.stock_data_provider.redis_client') as mock:
            # Setup get to return None (cache miss) by default
            mock.get = AsyncMock(return_value=None)
            mock.set = AsyncMock()
            mock.initialize = AsyncMock()
            mock.close = AsyncMock()
            yield mock

    @pytest.mark.asyncio
    async def test_initialization(self, mock_redis):
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
        """Test successful quote fetch with batch API mock"""
        provider = StockDataProvider()
        await provider.initialize()

        # Mock batch response structure
        mock_response = {
            'quotes': [
                {'code': '600519', 'price': 1850.0, 'volume': 150000},
                {'code': '000001', 'price': 15.0, 'volume': 1000000}
            ]
        }

        with patch.object(provider, '_make_request', new=AsyncMock(return_value=mock_response)):
            df = await provider.get_realtime_quotes(['600519', '000001'])
            assert len(df) == 2
            assert '600519' in df['code'].values
            assert '000001' in df['code'].values

        await provider.close()

    @pytest.mark.asyncio
    async def test_get_financial_data(self):
        """Test fetching financial indicators"""
        provider = StockDataProvider()
        await provider.initialize()

        mock_data = {
            'stock_code': '600519',
            'report_date': '2025-03-31',
            'roe': 15.5,
            'net_profit_growth_yoy': 12.3
        }

        with patch.object(provider, '_make_request', new=AsyncMock(return_value=mock_data)):
            data = await provider.get_financial_indicators('600519')
            assert data is not None
            assert data.stock_code == '600519'
            assert data.roe == 15.5

        await provider.close()

    @pytest.mark.asyncio
    async def test_get_valuation(self):
        """Test fetching valuation data"""
        provider = StockDataProvider()
        await provider.initialize()

        mock_data = {
            'stock_code': '600519',
            'pe_ttm': 30.5,
            'pb_ratio': 8.2
        }

        with patch.object(provider, '_make_request', new=AsyncMock(return_value=mock_data)):
            data = await provider.get_valuation('600519')
            assert data['stock_code'] == '600519'
            assert data['pe_ttm'] == 30.5

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

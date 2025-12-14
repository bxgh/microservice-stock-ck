
import pytest
import asyncio
from unittest.mock import AsyncMock
import pandas as pd
from datetime import datetime
from src.data_services.industry_service import IndustryService

@pytest.mark.asyncio
async def test_get_industry_info():
    # Mock cache manager
    mock_cache = AsyncMock()
    mock_cache.initialize.return_value = True
    mock_cache.get.return_value = None
    
    service = IndustryService(cache_manager=mock_cache, enable_cache=True)
    await service.initialize()
    
    # Mock akshare_client.call
    async def mock_call_akshare(*args, **kwargs):
        if args[0] == 'stock_individual_info_em':
            # Mock successful response
            return pd.DataFrame({
                'item': ['股票代码', '股票简称', '行业', '上市时间', '总市值'],
                'value': ['600519', '贵州茅台', '酿酒行业', '20010827', 1000000000.0]
            })
        return None

    # Patch global akshare_client
    from src.data_services.akshare_client import akshare_client
    akshare_client.call = AsyncMock(side_effect=mock_call_akshare)
    
    # Test
    info = await service.get_industry_info("600519")
    
    print("\nExtracted Info:", info)
    
    assert info['industry'] == "酿酒行业"
    assert info['listing_date'] == datetime(2001, 8, 27)
    
    print("✅ Logic Verified Successfully")

if __name__ == "__main__":
    asyncio.run(test_get_industry_info())

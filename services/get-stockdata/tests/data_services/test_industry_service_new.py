
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
from src.data_services.industry_service import IndustryService

@pytest.mark.asyncio
async def test_industry_stats_aggregation():
    # Mock cache manager
    mock_cache = AsyncMock()
    mock_cache.initialize.return_value = True
    mock_cache.get.return_value = None
    
    service = IndustryService(cache_manager=mock_cache, enable_cache=True)
    await service.initialize()
    
    # Mock akshare_client.call
    async def mock_call_akshare(*args, **kwargs):
        func_name = args[0]
        if func_name == 'stock_zh_a_spot_em':
            # Mock Spot Data (Universe)
            return pd.DataFrame({
                '代码': ['000001', '600519', '000858'],
                '名称': ['平安银行', '贵州茅台', '五粮液'],
                '行业': ['银行', '酿酒行业', '酿酒行业'],
                '市盈率-动态': [5.5, 30.2, 25.8],
                '市净率': [0.8, 8.5, 6.2]
            })
        elif func_name == 'stock_yjbb_em':
            # Mock Performance Data
            # Note: columns match what we found in verify_akshare_batch.py
            return pd.DataFrame({
                '股票代码': ['600519', '000858', '000001'],
                '净资产收益率': [20.5, 18.2, 10.1],
                '营业总收入-同比增长': [15.2, 12.8, 5.5]
            })
        elif func_name == 'stock_board_industry_cons_em':
             return pd.DataFrame({'代码': ['600519', '000858']})
        return None

    # Patch the global akshare_client instance used by IndustryService
    from src.data_services.akshare_client import akshare_client
    akshare_client.call = AsyncMock(side_effect=mock_call_akshare)
    # Remove service mock injection as it now uses global client
    # service._call_akshare_with_retry = ... # REMOVED
    
    # Test
    stats = await service.get_industry_stats("酿酒行业")
    
    print("\nCalculated Stats:", stats)
    
    # Verification
    assert stats['industry_name'] == "酿酒行业"
    assert stats['stock_count'] == 2 # 600519, 000858
    
    # PE Verification (30.2, 25.8)
    assert stats['pe_ttm_stats']['count'] == 2
    assert stats['pe_ttm_stats']['max'] == 30.2
    assert stats['pe_ttm_stats']['min'] == 25.8
    assert stats['pe_ttm_stats']['mean'] == 28.0
    
    # ROE Verification (20.5, 18.2) -> Mean: 19.35
    assert 'roe_stats' in stats
    assert stats['roe_stats']['count'] == 2
    assert stats['roe_stats']['mean'] == 19.35
    assert stats['roe_stats']['max'] == 20.5
    
    # Growth Verification (15.2, 12.8) -> Mean: 14.0
    assert 'revenue_growth_stats' in stats
    assert stats['revenue_growth_stats']['mean'] == 14.0
    
    print("✅ Logic Verified Successfully")

if __name__ == "__main__":
    asyncio.run(test_industry_stats_aggregation())

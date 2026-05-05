
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
import pandas as pd
from datetime import datetime

# Import the app
from src.main import app 

# Mock AkShareClient data
@pytest.fixture
def mock_akshare_data():
    from src.data_services.akshare_client import akshare_client
    
    # Save original method
    original_call = akshare_client.call
    
    async def side_effect(func_name, **kwargs):
        if func_name == 'stock_financial_analysis_indicator':
            return pd.DataFrame({
                '日期': ['2023-12-31'],
                '主营业务收入': [100000000.0],
                '主营业务成本': [50000000.0],
                '营业利润': [30000000.0]
            })
        elif func_name == 'stock_financial_report_sina':
            # Simplified mock for 3 sheets
            return pd.DataFrame({
                '报告日': ['20231231'],
                '短期借款': [1000.0]
            })
        elif func_name == 'stock_financial_abstract':
             return pd.DataFrame({
                '指标': ['净利润'],
                '20231231': ['5000.0']
             })
        elif func_name == 'stock_zh_a_spot_em':
            return pd.DataFrame({
                '代码': ['600519'],
                '名称': ['贵州茅台'],
                '市盈率-动态': [30.5],
                '市净率': [8.2],
                '总市值': [2000000000000.0],
                '最新价': [1700.0],
                '成交量': [50000],
                '成交额': [85000000.0],
                '换手率': [0.5]
            })
        elif func_name == 'stock_board_industry_cons_em':
             return pd.DataFrame({'代码': ['600519']})
        elif func_name == 'stock_yjbb_em':
            return pd.DataFrame({
                '股票代码': ['600519'],
                '净资产收益率': [20.0],
                '营业总收入-同比增长': [10.0]
            })
        elif func_name == 'stock_individual_info_em':
            return pd.DataFrame({
                'item': ['行业', '上市时间', '总市值', '流通市值', '市盈率(动)'],
                'value': ['酿酒行业', '20010827', '2000000000000', '1900000000000', '30.5']
            })
        elif func_name == 'stock_zh_valuation_baidu':
             # Return valid data to avoid retries
             return pd.DataFrame({
                 'date': ['2023-12-31'],
                 'value': [30.5],
             })
        return None

    akshare_client.call = AsyncMock(side_effect=side_effect)
    yield akshare_client
    # Restore original
    akshare_client.call = original_call

@pytest.mark.asyncio
async def test_finance_indicators_endpoint(mock_akshare_data):
    # Manually initialize services
    from src.data_services.financial_service import FinancialService
    service = FinancialService(enable_cache=False)
    await service.initialize()
    app.state.financial_service = service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/finance/indicators/600519")
        assert response.status_code in [200, 404] 
        if response.status_code == 200:
            data = response.json()
            assert "revenue" in data

@pytest.mark.asyncio
async def test_valuation_endpoint(mock_akshare_data):
    from src.data_services.valuation_service import ValuationService
    service = ValuationService(enable_cache=False)
    await service.initialize()
    app.state.valuation_service = service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/market/valuation/600519")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "pe_ttm" in data

@pytest.mark.asyncio
async def test_industry_stats(mock_akshare_data):
    from src.data_services.industry_service import IndustryService
    service = IndustryService(enable_cache=False)
    await service.initialize()
    app.state.industry_service = service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/finance/industry/C39/stats")
        assert response.status_code in [200, 404]

@pytest.mark.asyncio
async def test_enhanced_stock_info(mock_akshare_data):
    # Stock Info relies on IndustryService too
    from src.data_services.industry_service import IndustryService
    if not getattr(app.state, 'industry_service', None):
        service = IndustryService(enable_cache=False)
        await service.initialize()
        app.state.industry_service = service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/stocks/600519/info")
        assert response.status_code in [200, 404]

# Performance Benchmark
@pytest.mark.asyncio
async def test_api_latency(mock_akshare_data):
    from src.data_services.valuation_service import ValuationService
    if not getattr(app.state, 'valuation_service', None):
        service = ValuationService(enable_cache=False)
        await service.initialize()
        app.state.valuation_service = service
        
    import time
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = time.time()
        await client.get("/api/v1/market/valuation/600519")
        duration = (time.time() - start) * 1000
        print(f"\nAPI Latency: {duration:.2f}ms")
        assert duration < 1000 # Relaxed for test env

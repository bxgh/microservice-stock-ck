import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import collectors
from collectors.financial_collector import FinancialCollector
from collectors.capital_flow_collector import CapitalFlowCollector
from collectors.valuation_collector import ValuationCollector
from collectors.shareholder_collector import ShareholderCollector

@pytest.fixture
def mock_pool():
    # pool.acquire() is not awaited, so MagicMock
    pool = MagicMock()
    # conn.cursor() is not awaited, so MagicMock
    conn = MagicMock()
    cursor = AsyncMock()
    
    # Mock connection context manager
    # async with pool.acquire() as conn:
    pc_cm = AsyncMock() 
    pool.acquire.return_value = pc_cm
    pc_cm.__aenter__.return_value = conn
    
    # Mock cursor context manager
    # async with conn.cursor() as cursor:
    cc_cm = AsyncMock()
    conn.cursor.return_value = cc_cm
    cc_cm.__aenter__.return_value = cursor
    
    return pool

@pytest.fixture
def mock_cloud_service():
    """Mock CloudSyncService._fetch_api to avoid real HTTP calls"""
    with patch('core.cloud_sync_service.CloudSyncService._fetch_api', new_callable=AsyncMock) as mock_fetch:
        yield mock_fetch

@pytest.mark.asyncio
async def test_financial_collector(mock_pool, mock_cloud_service):
    # Setup
    mock_cloud_service.return_value = {
        "total_revenue": 1000.0,
        "net_profit": 200.0,
        "roe": 0.15,
        "report_date": "2024-03-31",
        "code": "600519"
    }
    
    collector = FinancialCollector(mock_pool)
    await collector.initialize()
    
    # Execute
    count = await collector.collect("600519")
    
    # Verify
    assert count == 1
    mock_cloud_service.assert_called_once()
    assert "stock_financial_local" in str(mock_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.execute.call_args)

@pytest.mark.asyncio
async def test_valuation_collector(mock_pool, mock_cloud_service):
    # Setup
    mock_cloud_service.return_value = {
        "name": "贵州茅台",
        "pe": 20.0,
        "pb": 5.0,
        "market_cap": 2000000.0,
        "price": 1000.0,
        "code": "600519"
    }
    
    collector = ValuationCollector(mock_pool)
    await collector.initialize()
    
    # Execute
    count = await collector.collect("600519")
    
    # Verify
    assert count == 1
    mock_cloud_service.assert_called_once()

@pytest.mark.asyncio
async def test_shareholder_collector(mock_pool, mock_cloud_service):
    # Setup
    mock_cloud_service.return_value = {
        "holder_count_history": [
            {"date": "2024-03-31", "count": 10000, "change": 5.0, "avg_market_cap": 100.0}
        ],
        "top10_holders": [
            {"rank": 1, "holder_name": "Holder A", "hold_count": 1000, "hold_pct": 10.0, "share_type": "A", "time": "2024-03-31"}
        ]
    }
    
    collector = ShareholderCollector(mock_pool)
    await collector.initialize()
    
    # Execute
    result = await collector.collect("600519")
    
    # Verify
    assert result["holder_count"] == 1
    assert result["top_holders"] == 1
    
    # Check that database execute was called twice (once for count, once for top holders)
    cursor_mock = mock_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    assert cursor_mock.execute.call_count == 2

@pytest.mark.asyncio
async def test_collector_api_failure(mock_pool, mock_cloud_service):
    # Setup - simulate API failure returning None
    mock_cloud_service.return_value = None
    
    collector = FinancialCollector(mock_pool)
    await collector.initialize()
    
    # Execute
    count = await collector.collect("600519")
    
    # Verify
    assert count == 0
    # DB Should NOT be called
    cursor_mock = mock_pool.acquire.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor_mock.execute.assert_not_called()

import sys
from unittest.mock import MagicMock, AsyncMock

# Mock dependencies to bypass environment restrictions
sys.modules["pydantic"] = MagicMock()
sys.modules["gsd_shared.models"] = MagicMock()
sys.modules["gsd_shared.models.kline"] = MagicMock()
sys.modules["gsd_shared.models.stock"] = MagicMock()
sys.modules["gsd_shared.models.sync"] = MagicMock()

import pytest
import asyncio
from datetime import datetime
import pytz

from gsd_shared.tick.fetcher import TickFetcher
from gsd_shared.tick.writer import TickWriter
from gsd_shared.tick.deduplicator import TickDeduplicator
from gsd_shared.tick.constants import MOOTDX_TICK_ENDPOINT, TABLE_INTRADAY_LOCAL, TABLE_HISTORY_LOCAL

# Mock CST time
CST = pytz.timezone('Asia/Shanghai')

@pytest.mark.asyncio
async def test_fetcher_realtime():
    """Test Fetcher in REALTIME mode"""
    mock_session = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = [{"time": "14:00", "price": 10.0, "vol": 100}]
    mock_session.get.return_value.__aenter__.return_value = mock_resp
    
    fetcher = TickFetcher(mock_session, "http://api", mode=TickFetcher.Mode.REALTIME)
    
    # Test strict prefix cleaning
    await fetcher.fetch("sh600519")
    
    # Verify URL call manually
    call_args = mock_session.get.call_args
    assert call_args[0][0] == "http://api/api/v1/tick/600519"
    assert call_args[1]["timeout"].total == 4

@pytest.mark.asyncio
async def test_fetcher_historical_param():
    """Test Fetcher in HISTORICAL mode passes date param"""
    mock_session = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = []
    mock_session.get.return_value.__aenter__.return_value = mock_resp
    
    fetcher = TickFetcher(mock_session, "http://api", mode=TickFetcher.Mode.HISTORICAL)
    
    # Passing a historical date
    await fetcher.fetch("000001", trade_date="20230101")
    
    # Verify params contains date
    call_args = mock_session.get.call_args
    assert "params" in call_args[1]
    assert call_args[1]["params"]["date"] == 20230101

def test_deduplicator():
    """Test Deduplicator logic (V2 Occurrence-shared)"""
    dedup = TickDeduplicator(cache_size=10)
    
    item1 = {"time": "10:00", "price": 10.0, "vol": 100}
    item2 = {"time": "10:00", "price": 10.0, "volume": 100} # Alias check
    item3 = {"time": "10:01", "price": 10.0, "vol": 100}
    
    # Batch 1
    dedup.reset_batch_counters()
    assert dedup.is_duplicate("600000", item1) == False
    
    # Same item in SAME batch should be treated as a SECOND distinct trade (if using different objects)
    # But for the EXACT same object, my code has idempotency logic
    assert dedup.is_duplicate("600000", item1) == True # Idempotency on same object
    
    # Different object with same content in SAME batch -> Distinct trade!
    assert dedup.is_duplicate("600000", item2) == False 
    
    # Batch 2 (Next polling round)
    dedup.reset_batch_counters()
    assert dedup.is_duplicate("600000", item1) == True # Duplicate across batches
    assert dedup.is_duplicate("600000", item2) == True # Duplicate across batches
    assert dedup.is_duplicate("600000", item3) == False # New content

@pytest.mark.asyncio
async def test_writer_routing_and_mapping():
    """Test Writer routing logic and field mapping"""
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    
    # pool.acquire() return CM -> enter -> conn
    mock_pool_acquire_ctx = MagicMock()
    mock_pool_acquire_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool_acquire_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool.acquire.return_value = mock_pool_acquire_ctx
    
    # conn.cursor() -> CM -> enter -> cursor
    # FIX: conn.cursor should NOT be async itself, it returns a CM whose __aenter__ is async
    # So we replace the auto-created AsyncMock with MagicMock
    mock_conn.cursor = MagicMock()

    mock_cursor_ctx = MagicMock()
    mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
    
    mock_conn.cursor.return_value = mock_cursor_ctx
    
    writer = TickWriter(mock_pool)
    
    # Test 1: Today -> INTRADAY table
    today_str = datetime.now(CST).strftime("%Y%m%d")
    data_today = [{"time": "09:30", "price": 10.0, "vol": 100, "type": "BUY"}]
    
    await writer.write("sh600519", today_str, data_today)
    
    # Verify table name in SQL (first arg of execute)
    sql_today = mock_cursor.execute.call_args[0][0]
    assert TABLE_INTRADAY_LOCAL in sql_today
    
    args_today = mock_cursor.execute.call_args[0][1]
    assert args_today[0][6] == 0  # 7th field is direction
    assert args_today[0][0] == "600519" # Cleaned code

    # Test 2: History -> HISTORY table
    await writer.write("sz000001", "20200101", [{"time": "09:30", "price": 10.0, "vol": 100, "buyorsell": 1}])
    
    # Verify table name
    sql_hist = mock_cursor.execute.call_args[0][0]
    assert TABLE_HISTORY_LOCAL in sql_hist
    
    args_hist = mock_cursor.execute.call_args[0][1]
    assert args_hist[0][6] == 1

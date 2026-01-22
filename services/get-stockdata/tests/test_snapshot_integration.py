import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import pytz
from src.core.collector.intraday_tick_collector import IntradayTickCollector

CST = pytz.timezone('Asia/Shanghai')

@pytest.fixture
def collector():
    collector = IntradayTickCollector()
    collector.initialize = AsyncMock()
    collector.stop = AsyncMock()
    return collector

@pytest.mark.asyncio
async def test_snapshot_batch_collection(collector):
    """测试快照分批采集逻辑"""
    collector.stock_pool = ["sh600000"]
    collector.snapshot_batches = [["sh600000"]]
    
    # 1. Mock HTTP Response
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = [{"code": "sh600000", "price": 10.5, "name": "浦发", "market": "SH"}]
    
    # 2. Mock HTTP Session GET context manager
    mock_get_cm = AsyncMock()
    mock_get_cm.__aenter__.return_value = mock_resp
    
    mock_session = MagicMock()
    mock_session.get.return_value = mock_get_cm
    collector.http_session = mock_session
    
    # 3. Mock ClickHouse Pool
    mock_cursor = AsyncMock()
    mock_cursor_cm = AsyncMock()
    mock_cursor_cm.__aenter__.return_value = mock_cursor
    
    # Connection object - cursor() is a regular method
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_cm
    
    # Acquire context manager
    mock_acquire_cm = AsyncMock()
    mock_acquire_cm.__aenter__.return_value = mock_conn
    
    collector.clickhouse_pool = MagicMock()
    collector.clickhouse_pool.acquire.return_value = mock_acquire_cm
    
    await collector._collect_snapshots()
    
    mock_session.get.assert_called_once()
    mock_cursor.execute.assert_called_once()

@pytest.mark.asyncio
async def test_snapshot_data_mapping(collector):
    """测试数据映射逻辑"""
    item = {"code": "sh600519", "name": "茅台", "market": "1", "price": 1700}
    today = datetime.now(CST).date()
    row = collector._map_snapshot_row(item, today, datetime.now(CST))
    assert row[2] == "600519"
    assert isinstance(row[4], str)

@pytest.mark.asyncio
async def test_snapshot_batch_failure_resilience(collector):
    """测试分批失败时的容错性"""
    collector.snapshot_batches = [["sh600001"], ["sh600002"]]
    mock_session = MagicMock()
    
    mock_resp = AsyncMock(status=200, json=AsyncMock(return_value=[]))
    mock_cm = AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))
    
    mock_session.get.side_effect = [Exception("Fail"), mock_cm]
    collector.http_session = mock_session
    
    await collector._collect_snapshots()
    assert mock_session.get.call_count == 2

@pytest.mark.asyncio
async def test_dual_loop_concurrent_safety(collector):
    """测试双协程并发安全"""
    collector._is_trading_time = lambda: False
    collector._shutdown_event.set()
    await collector._snapshot_loop()
    await collector._tick_loop()

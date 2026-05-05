import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.collector.intraday_tick_collector import IntradayTickCollector

@pytest.fixture
def collector():
    # Mock the stock pool path to a valid one if needed, but we can set stock_pool directly
    c = IntradayTickCollector(stock_pool_path="/app/config/hs300_stocks.yaml")
    c.stock_pool = ["sh600519"]
    c.fingerprints = {"sh600519": []}
    return c

@pytest.mark.asyncio
async def test_gen_fingerprint(collector):
    item1 = {"time": "09:30", "price": 1800.0, "volume": 100, "type": "BUY"}
    item2 = {"time": "09:30", "price": 1800.0, "volume": 100, "type": "BUY"}
    item3 = {"time": "09:31", "price": 1800.0, "volume": 100, "type": "BUY"}
    
    fp1 = collector._gen_fingerprint(item1)
    fp2 = collector._gen_fingerprint(item2)
    fp3 = collector._gen_fingerprint(item3)
    
    assert fp1 == fp2
    assert fp1 != fp3

@pytest.mark.asyncio
async def test_poll_stock_deduplication(collector):
    # Mock HTTP response
    mock_ticks = [
        {"time": "09:30", "price": 1800.0, "volume": 100, "type": "BUY"},
        {"time": "09:31", "price": 1801.0, "volume": 200, "type": "SELL"}
    ]
    
    collector._fetch_stock_ticks = AsyncMock(return_value=mock_ticks)
    collector.clickhouse_pool = MagicMock()
    
    # First poll
    await collector.poll_stock("sh600519")
    assert len(collector.write_buffer) == 2
    assert len(collector.fingerprints["sh600519"]) == 2
    
    # Second poll with same data
    await collector.poll_stock("sh600519")
    assert len(collector.write_buffer) == 2 # Should not increase
    
    # Third poll with one new item
    mock_ticks.append({"time": "09:32", "price": 1802.0, "volume": 300, "type": "BUY"})
    collector._fetch_stock_ticks = AsyncMock(return_value=mock_ticks)
    await collector.poll_stock("sh600519")
    assert len(collector.write_buffer) == 3
    assert len(collector.fingerprints["sh600519"]) == 3

@pytest.mark.asyncio
async def test_map_direction(collector):
    assert collector._map_direction("BUY") == 0
    assert collector._map_direction("SELL") == 1
    assert collector._map_direction("NEUTRAL") == 2
    assert collector._map_direction("UNKNOWN") == 2

@pytest.mark.asyncio
async def test_concurrent_poll_stock(collector):
    """测试并发 poll_stock 的线程安全性 (P2 FIX)"""
    # Mock HTTP response
    mock_ticks = [
        {"time": "09:30", "price": 1800.0, "volume": 100, "type": "BUY"},
        {"time": "09:31", "price": 1801.0, "volume": 200, "type": "SELL"}
    ]
    
    collector._fetch_stock_ticks = AsyncMock(return_value=mock_ticks)
    collector.clickhouse_pool = MagicMock()
    
    # 并发100次调用 poll_stock
    tasks = [collector.poll_stock("sh600519") for _ in range(100)]
    await asyncio.gather(*tasks)
    
    # 验证 write_buffer 的数据完整性
    # 由于指纹去重,相同的数据只会被添加一次,所以应该只有2条
    # 关键是验证并发安全:没有数据丢失或损坏
    assert len(collector.write_buffer) == 2  # 去重后只有2条唯一数据
    assert len(collector.fingerprints["sh600519"]) == 2  # 指纹缓存也是2条


@pytest.mark.asyncio
async def test_concurrent_flush(collector):
    """测试并发 flush_to_clickhouse 的线程安全性 (P2 FIX)"""
    # 预填充 write_buffer
    for i in range(100):
        collector.write_buffer.append((
            "600519", "2026-01-13", f"09:30:{i:02d}", 1800.0, 100, 180000.0, 0
        ))
    
    # Mock ClickHouse pool
    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    collector.clickhouse_pool = MagicMock()
    collector.clickhouse_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    # 并发10次 flush
    tasks = [collector.flush_to_clickhouse() for _ in range(10)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # 验证 buffer 已清空
    assert len(collector.write_buffer) == 0

if __name__ == '__main__':
    import sys
    import os
    # Ensure src is in path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
    
    # Try to import pytest and run
    try:
        import pytest
        sys.exit(pytest.main([__file__, '-v']))
    except ImportError:
        print("pytest not found, attempting to install...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"])
        import pytest
        sys.exit(pytest.main([__file__, '-v']))

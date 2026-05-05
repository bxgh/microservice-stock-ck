import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from src.data.cache import ParquetCache, CachedDataSource
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def temp_cache_dir(tmp_path):
    return tmp_path / "cache"

@pytest.fixture
def parquet_cache(temp_cache_dir):
    return ParquetCache(cache_dir=temp_cache_dir)

def test_parquet_cache_set_get(parquet_cache):
    """测试基本的缓存存取"""
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "close": [10.0, 11.0]
    })
    
    params = {"symbol": "000001.SZ", "start": "2024-01-01"}
    parquet_cache.set("kline", df, **params)
    
    cached_df = parquet_cache.get("kline", **params)
    assert cached_df is not None
    assert len(cached_df) == 2
    assert cached_df["close"].iloc[1] == 11.0

def test_parquet_cache_ttl(parquet_cache, temp_cache_dir):
    """测试缓存过期逻辑"""
    df = pd.DataFrame({"a": [1]})
    params = {"id": 1}
    parquet_cache.set("test", df, **params)
    
    # 模拟过期：通过修改文件修改时间
    filename = parquet_cache._generate_key("test", **params)
    file_path = temp_cache_dir / filename
    
    # 设置为 25 小时前
    past_time = (datetime.now() - timedelta(hours=25)).timestamp()
    import os
    os.utime(file_path, (past_time, past_time))
    
    # 默认 TTL 是 24 小时，现在应该拿不到了
    assert parquet_cache.get("test", **params) is None
    
    # 如果覆盖 TTL 为 48 小时，应该能拿到
    assert parquet_cache.get("test", ttl_override=timedelta(hours=48), **params) is not None

@pytest.mark.asyncio
async def test_cached_data_source_historical_logic(parquet_cache):
    """测试 CachedDataSource 的冷热数据逻辑"""
    mock_source = MagicMock()
    mock_source.fetch_kline = AsyncMock()
    
    cached_source = CachedDataSource(mock_source, parquet_cache)
    
    # 1. 测试历史数据 (10 天前)
    hist_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    df_hist = pd.DataFrame({"date": [hist_date], "close": [100.0]})
    mock_source.fetch_kline.return_value = df_hist
    
    # 第一次取，调用源
    res1 = await cached_source.fetch_kline("000001.SZ", "2024-01-01", end_date=hist_date)
    assert mock_source.fetch_kline.call_count == 1
    
    # 第二次取，命中缓存
    res2 = await cached_source.fetch_kline("000001.SZ", "2024-01-01", end_date=hist_date)
    assert mock_source.fetch_kline.call_count == 1
    assert res2["close"].iloc[0] == 100.0
    
    # 2. 测试近期数据 (今天)
    today_str = datetime.now().strftime("%Y-%m-%d")
    df_today = pd.DataFrame({"date": [today_str], "close": [200.0]})
    mock_source.fetch_kline.return_value = df_today
    
    await cached_source.fetch_kline("000001.SZ", "2024-01-01", end_date=today_str)
    assert mock_source.fetch_kline.call_count == 2

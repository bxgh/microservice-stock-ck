"""
测试 StockPoolManager 的新功能

Story 004.01: 初始股票池管理
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from pathlib import Path
from src.core.stock_pool.manager import StockPoolManager

@pytest.fixture
def pool_manager(tmp_path):
    """创建临时缓存目录的 StockPoolManager"""
    cache_dir = tmp_path / "stock_pools"
    return StockPoolManager(cache_dir=str(cache_dir))

@pytest.mark.asyncio
async def test_get_hs300_top100_success(pool_manager):
    """测试成功获取沪深300 Top100"""
    # Mock akshare API
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.__len__ = lambda self: 300
    mock_df.__getitem__ = lambda self, key: {
        '品种代码': MagicMock(tolist=lambda: [f"{i:06d}" for i in range(300)]),
        '品种名称': MagicMock(__getitem__=lambda self, cond: MagicMock(iloc=[MagicMock(__getitem__=lambda self, i: f"Stock{i}")]))
    }[key]
    
    with patch('akshare.index_stock_cons', return_value=mock_df):
        # Mock _get_avg_volume 返回递减的成交额
        async def mock_get_volume(code, days):
            code_num = int(code)
            return 10000000000 - (code_num * 1000000)  # 递减
        
        pool_manager._get_avg_volume = mock_get_volume
        
        stocks = await pool_manager.get_hs300_top100_by_volume()
        
        assert len(stocks) == 100
        assert all(isinstance(code, str) for code in stocks)
        # 第一个应该是成交额最大的（代码最小）
        assert stocks[0] == "000000"

@pytest.mark.asyncio
async def test_cache_fallback_on_api_failure(pool_manager, tmp_path):
    """测试API失败时从缓存加载"""
    # 先创建一个缓存文件
    cache_data = {
        "updated_at": datetime.now().isoformat(),
        "pool_name": "hs300_top100",
        "count": 50,
        "stocks": [{"code": f"{i:06d}", "name": f"Stock{i}", "avg_amount": 1000000} for i in range(50)]
    }
    
    cache_file = pool_manager.cache_dir / f"hs300_top100_{datetime.now().strftime('%Y%m%d')}.json"
    pool_manager.cache_dir.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f)
    
    # Mock akshare API 失败
    with patch('akshare.index_stock_cons', side_effect=Exception("API Error")):
        stocks = await pool_manager.get_hs300_top100_by_volume()
        
        # 应该从缓存加载
        assert len(stocks) == 50
        assert stocks[0] == "000000"

@pytest.mark.asyncio
async def test_get_avg_volume(pool_manager):
    """测试获取平均成交额"""
    # Mock akshare stock_zh_a_hist
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.tail = lambda days: MagicMock(
        __getitem__=lambda self, key: MagicMock(
            mean=lambda: 5000000000 if key == '成交额' else None
        ),
        columns=['成交额']
    )
    
    with patch('akshare.stock_zh_a_hist', return_value=mock_df):
        avg_amount = await pool_manager._get_avg_volume("600519", 5)
        
        assert avg_amount == 5000000000

@pytest.mark.asyncio
async def test_get_avg_volume_no_data(pool_manager):
    """测试无数据时返回0"""
    with patch('akshare.stock_zh_a_hist', return_value=None):
        avg_amount = await pool_manager._get_avg_volume("600519", 5)
        assert avg_amount == 0.0

@pytest.mark.asyncio
async def test_save_and_load_cache(pool_manager):
    """测试缓存保存和加载"""
    stocks = [
        {"code": "600519", "name": "贵州茅台", "avg_amount": 15000000000},
        {"code": "000858", "name": "五粮液", "avg_amount": 12000000000}
    ]
    
    # 保存缓存
    await pool_manager._save_pool_cache(stocks, "test_pool")
    
    # 加载缓存
    loaded_stocks = await pool_manager._load_pool_cache("test_pool")
    
    assert len(loaded_stocks) == 2
    assert loaded_stocks[0] == "600519"
    assert loaded_stocks[1] == "000858"

@pytest.mark.asyncio
async def test_load_cache_not_found(pool_manager):
    """测试缓存不存在时返回空列表"""
    stocks = await pool_manager._load_pool_cache("nonexistent_pool")
    assert stocks == []

@pytest.mark.asyncio
async def test_cleanup_old_caches(pool_manager):
    """测试清理旧缓存"""
    # 创建几个不同日期的缓存文件
    from datetime import timedelta
    
    for days_ago in [1, 5, 10]:
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
        cache_file = pool_manager.cache_dir / f"test_pool_{date}.json"
        pool_manager.cache_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(cache_file, "w") as f:
            json.dump({"stocks": []}, f)
    
    # 清理超过7天的缓存
    await pool_manager._cleanup_old_caches("test_pool", max_age_days=7)
    
    # 检查文件数量
    remaining_files = list(pool_manager.cache_dir.glob("test_pool_*.json"))
    # 10天前的应该被删除，1天和5天前的保留
    assert len(remaining_files) == 2

@pytest.mark.asyncio
async def test_backward_compatibility(pool_manager):
    """测试向后兼容性 - 原有的 initialize_static_l1_pool 仍然工作"""
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.__getitem__ = lambda self, key: MagicMock(tolist=lambda: ["600519", "000858", "600036"])
    
    with patch('akshare.index_stock_cons', return_value=mock_df):
        count = pool_manager.initialize_static_l1_pool()
        
        assert count == 3
        from src.core.stock_pool.manager import PoolLevel
        assert len(pool_manager.get_pool_symbols(PoolLevel.L1_CORE)) == 3

"""
测试 AcquisitionScheduler 与 StockPoolManager 的集成

Story 004.01: 初始股票池管理
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.core.scheduling.scheduler import AcquisitionScheduler
from src.core.stock_pool.manager import StockPoolManager

@pytest.mark.asyncio
async def test_scheduler_initialize_with_pool():
    """测试调度器初始化时加载股票池"""
    scheduler = AcquisitionScheduler()
    
    # Mock pool_manager.get_hs300_top100_by_volume
    async def mock_get_pool(lookback_days):
        return [f"{i:06d}" for i in range(100)]
    
    scheduler.pool_manager.get_hs300_top100_by_volume = mock_get_pool
    
    # 初始化
    await scheduler.initialize()
    
    # 验证股票池已加载
    pool = scheduler.get_current_pool()
    assert len(pool) == 100
    assert pool[0] == "000000"
    assert pool[99] == "000099"

@pytest.mark.asyncio
async def test_scheduler_initialize_empty_pool_warning():
    """测试股票池为空时发出警告"""
    scheduler = AcquisitionScheduler()
    
    # Mock pool_manager 返回空池
    async def mock_get_empty_pool(lookback_days):
        return []
    
    scheduler.pool_manager.get_hs300_top100_by_volume = mock_get_empty_pool
    
    # 初始化（应该记录警告但不抛出异常）
    await scheduler.initialize()
    
    pool = scheduler.get_current_pool()
    assert len(pool) == 0

@pytest.mark.asyncio
async def test_scheduler_initialize_failure():
    """测试初始化失败时抛出异常"""
    scheduler = AcquisitionScheduler()
    
    # Mock pool_manager 抛出异常
    async def mock_get_pool_error(lookback_days):
        raise Exception("Test Error")
    
    scheduler.pool_manager.get_hs300_top100_by_volume = mock_get_pool_error
    
    # 初始化应该抛出异常
    with pytest.raises(Exception):
        await scheduler.initialize()

@pytest.mark.asyncio
async def test_get_current_pool_returns_copy():
    """测试 get_current_pool 返回副本而非引用"""
    scheduler = AcquisitionScheduler()
    
    # 设置测试池
    scheduler.current_pool = ["600519", "000858"]
    
    # 获取池
    pool1 = scheduler.get_current_pool()
    pool2 = scheduler.get_current_pool()
    
    # 修改pool1不应影响pool2
    pool1.append("600036")
    
    assert len(pool2) == 2
    assert len(scheduler.current_pool) == 2

@pytest.mark.asyncio
async def test_refresh_pool_success():
    """测试刷新股票池成功"""
    scheduler = AcquisitionScheduler()
    
    # 初始池
    scheduler.current_pool = [f"{i:06d}" for i in range(50)]
    
    # Mock 新池
    async def mock_get_new_pool(lookback_days):
        return [f"{i:06d}" for i in range(100, 200)]
    
    scheduler.pool_manager.get_hs300_top100_by_volume = mock_get_new_pool
    
    # 刷新
    await scheduler.refresh_pool()
    
    # 验证池已更新
    pool = scheduler.get_current_pool()
    assert len(pool) == 100
    assert pool[0] == "000100"

@pytest.mark.asyncio
async def test_refresh_pool_empty_keeps_old():
    """测试刷新返回空池时保留旧池"""
    scheduler = AcquisitionScheduler()
    
    # 初始池
    old_pool = [f"{i:06d}" for i in range(50)]
    scheduler.current_pool = old_pool.copy()
    
    # Mock 返回空池
    async def mock_get_empty_pool(lookback_days):
        return []
    
    scheduler.pool_manager.get_hs300_top100_by_volume = mock_get_empty_pool
    
    # 刷新
    await scheduler.refresh_pool()
    
    # 应该保留旧池
    pool = scheduler.get_current_pool()
    assert len(pool) == 50
    assert pool == old_pool

@pytest.mark.asyncio
async def test_refresh_pool_error_keeps_old():
    """测试刷新失败时保留旧池"""
    scheduler = AcquisitionScheduler()
    
    # 初始池
    old_pool = [f"{i:06d}" for i in range(50)]
    scheduler.current_pool = old_pool.copy()
    
    # Mock 抛出异常
    async def mock_get_pool_error(lookback_days):
        raise Exception("API Error")
    
    scheduler.pool_manager.get_hs300_top100_by_volume = mock_get_pool_error
    
    # 刷新（不应抛出异常）
    await scheduler.refresh_pool()
    
    # 应该保留旧池
    pool = scheduler.get_current_pool()
    assert len(pool) == 50
    assert pool == old_pool

@pytest.mark.asyncio
async def test_scheduler_backward_compatibility():
    """测试调度器的原有功能不受影响"""
    scheduler = AcquisitionScheduler()
    
    # 原有方法应该仍然工作
    assert hasattr(scheduler, 'should_run_now')
    assert hasattr(scheduler, 'wait_for_next_run')
    assert hasattr(scheduler, '_get_next_start_time')
    
    # 新增方法存在
    assert hasattr(scheduler, 'initialize')
    assert hasattr(scheduler, 'get_current_pool')
    assert hasattr(scheduler, 'refresh_pool')

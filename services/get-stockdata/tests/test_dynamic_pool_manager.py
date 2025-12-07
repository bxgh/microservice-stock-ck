"""
Test DynamicPoolManager
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from services.stock_pool.dynamic_pool_manager import DynamicPoolManager
from services.stock_pool.anomaly_detector import AnomalyStock

@pytest.mark.asyncio
async def test_promote_stock():
    """测试股票晋升"""
    manager = DynamicPoolManager(max_dynamic_size=2)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    
    anomaly = AnomalyStock(
        code="000001", name="Test1", trigger_reason="涨幅",
        trigger_value=5.0, detected_at=now,
        expire_at=now + timedelta(minutes=30)
    )
    
    await manager.promote(anomaly)
    assert len(manager.promoted_stocks) == 1
    assert "000001" in manager.promoted_stocks

@pytest.mark.asyncio
async def test_pool_capacity_eviction():
    """测试容量限制和FIFO驱逐"""
    manager = DynamicPoolManager(max_dynamic_size=2)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    
    # 添加3个股票
    for i in range(3):
        anomaly = AnomalyStock(
            code=f"00000{i}", name=f"Test{i}", trigger_reason="涨幅",
            trigger_value=5.0, detected_at=now,
            expire_at=now + timedelta(minutes=30)
        )
        await manager.promote(anomaly)
        
    # 应该只有2个，000000被移除
    assert len(manager.promoted_stocks) == 2
    assert "000000" not in manager.promoted_stocks
    assert "000001" in manager.promoted_stocks
    assert "000002" in manager.promoted_stocks

@pytest.mark.asyncio
async def test_manual_add_remove():
    """测试手动添加和移除"""
    manager = DynamicPoolManager()
    
    await manager.add_manual("600000", duration_minutes=60)
    assert "600000" in manager.manual_stocks
    
    stocks = await manager.get_all_dynamic_stocks()
    assert "600000" in stocks
    
    await manager.remove_manual("600000")
    assert "600000" not in manager.manual_stocks

@pytest.mark.asyncio
async def test_cleanup_expired():
    """测试过期清理"""
    manager = DynamicPoolManager()
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    
    # 添加过期股票
    anomaly = AnomalyStock(
        code="000001", name="Test1", trigger_reason="涨幅",
        trigger_value=5.0, detected_at=now,
        expire_at=now - timedelta(minutes=1) # 已过期
    )
    await manager.promote(anomaly)
    
    await manager.cleanup_expired()
    assert len(manager.promoted_stocks) == 0

@pytest.mark.asyncio
async def test_get_all_unique():
    """测试获取去重后的所有股票"""
    manager = DynamicPoolManager()
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    
    # 晋升 000001
    anomaly = AnomalyStock(
        code="000001", name="Test1", trigger_reason="涨幅",
        trigger_value=5.0, detected_at=now,
        expire_at=now + timedelta(minutes=30)
    )
    await manager.promote(anomaly)
    
    # 手动添加 000001 (重复) 和 600000
    await manager.add_manual("000001")
    await manager.add_manual("600000")
    
    stocks = await manager.get_all_dynamic_stocks()
    assert len(stocks) == 2
    assert "000001" in stocks
    assert "600000" in stocks

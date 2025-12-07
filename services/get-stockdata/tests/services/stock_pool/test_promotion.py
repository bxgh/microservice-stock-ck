"""
Tests for PromotionMonitor and DynamicPoolManager (Story 004.03)
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from zoneinfo import ZoneInfo

from services.stock_pool.dynamic_pool_manager import DynamicPoolManager
from services.stock_pool.anomaly_detector import AnomalyStock
from services.stock_pool.promotion_monitor import PromotionMonitor


CST = ZoneInfo("Asia/Shanghai")


class TestDynamicPoolManager:
    """Tests for DynamicPoolManager"""
    
    @pytest.fixture
    def pool_manager(self):
        return DynamicPoolManager(max_dynamic_size=5)
    
    @pytest.mark.asyncio
    async def test_promote_stock(self, pool_manager):
        """Test promoting a stock to dynamic pool"""
        now = datetime.now(CST)
        anomaly = AnomalyStock(
            code="000001",
            name="平安银行",
            trigger_reason="飙升榜Top1",
            trigger_value=1.0,
            detected_at=now,
            expire_at=now + timedelta(minutes=30)
        )
        
        await pool_manager.promote(anomaly)
        
        stocks = await pool_manager.get_all_dynamic_stocks()
        assert "000001" in stocks
    
    @pytest.mark.asyncio
    async def test_promote_max_capacity(self, pool_manager):
        """Test FIFO eviction when pool is at max capacity"""
        now = datetime.now(CST)
        
        # Add 5 stocks (max capacity)
        for i in range(5):
            anomaly = AnomalyStock(
                code=f"00000{i}",
                name=f"股票{i}",
                trigger_reason="飙升榜",
                trigger_value=float(i),
                detected_at=now,
                expire_at=now + timedelta(minutes=30)
            )
            await pool_manager.promote(anomaly)
        
        # Verify all 5 are in pool
        stocks = await pool_manager.get_all_dynamic_stocks()
        assert len(stocks) == 5
        assert "000000" in stocks  # First stock still there
        
        # Add 6th stock - should evict first
        anomaly = AnomalyStock(
            code="000005",
            name="新股票",
            trigger_reason="飙升榜Top1",
            trigger_value=5.0,
            detected_at=now,
            expire_at=now + timedelta(minutes=30)
        )
        await pool_manager.promote(anomaly)
        
        stocks = await pool_manager.get_all_dynamic_stocks()
        assert len(stocks) == 5
        assert "000000" not in stocks  # First stock evicted
        assert "000005" in stocks  # New stock added
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, pool_manager):
        """Test cleanup of expired stocks"""
        now = datetime.now(CST)
        
        # Add an already expired stock
        expired_anomaly = AnomalyStock(
            code="000001",
            name="已过期",
            trigger_reason="飙升榜",
            trigger_value=1.0,
            detected_at=now - timedelta(minutes=60),
            expire_at=now - timedelta(minutes=30)  # Expired 30 mins ago
        )
        await pool_manager.promote(expired_anomaly)
        
        # Add a fresh stock
        fresh_anomaly = AnomalyStock(
            code="000002",
            name="新鲜",
            trigger_reason="飙升榜",
            trigger_value=2.0,
            detected_at=now,
            expire_at=now + timedelta(minutes=30)
        )
        await pool_manager.promote(fresh_anomaly)
        
        # Cleanup
        await pool_manager.cleanup_expired()
        
        stocks = await pool_manager.get_all_dynamic_stocks()
        assert "000001" not in stocks  # Expired, removed
        assert "000002" in stocks  # Still valid
    
    @pytest.mark.asyncio
    async def test_manual_add_remove(self, pool_manager):
        """Test manual stock addition and removal"""
        await pool_manager.add_manual("600519", duration_minutes=60)
        
        stocks = await pool_manager.get_all_dynamic_stocks()
        assert "600519" in stocks
        
        await pool_manager.remove_manual("600519")
        
        stocks = await pool_manager.get_all_dynamic_stocks()
        assert "600519" not in stocks
    
    @pytest.mark.asyncio
    async def test_get_stats(self, pool_manager):
        """Test stats retrieval"""
        now = datetime.now(CST)
        anomaly = AnomalyStock(
            code="000001",
            name="测试",
            trigger_reason="飙升榜",
            trigger_value=1.0,
            detected_at=now,
            expire_at=now + timedelta(minutes=30)
        )
        await pool_manager.promote(anomaly)
        await pool_manager.add_manual("600519")
        
        stats = await pool_manager.get_stats()
        
        assert stats["promoted_count"] == 1
        assert stats["manual_count"] == 1
        assert stats["total_dynamic"] == 2
        assert stats["max_capacity"] == 5


class TestPromotionMonitor:
    """Tests for PromotionMonitor"""
    
    @pytest.fixture
    def mock_ranking_service(self):
        """Create a mock RankingService"""
        mock = AsyncMock()
        mock.get_surge_rank.return_value = pd.DataFrame([
            {"代码": "000001", "名称": "平安银行", "涨幅": 5.5},
            {"代码": "000002", "名称": "万科A", "涨幅": 4.2},
            {"代码": "600519", "名称": "贵州茅台", "涨幅": 3.8},
        ])
        return mock
    
    @pytest.fixture
    def pool_manager(self):
        return DynamicPoolManager(max_dynamic_size=20)
    
    @pytest.fixture
    def monitor(self, pool_manager, mock_ranking_service):
        return PromotionMonitor(
            dynamic_pool=pool_manager,
            ranking_service=mock_ranking_service,
            scan_interval=60,
            top_n=20,
            ttl_minutes=30
        )
    
    def test_initialization(self, monitor):
        """Test monitor initialization"""
        assert monitor.scan_interval == 60
        assert monitor.top_n == 20
        assert monitor.ttl_minutes == 30
        assert monitor._running == False
    
    @pytest.mark.asyncio
    async def test_scan_and_promote(self, monitor, pool_manager):
        """Test scanning surge rank and promoting stocks"""
        # Force scan (bypasses trading hours check)
        await monitor._scan_and_promote()
        
        # Verify stocks were promoted
        stocks = await pool_manager.get_all_dynamic_stocks()
        assert "000001" in stocks
        assert "000002" in stocks
        assert "600519" in stocks
        
        # Verify stats
        stats = monitor.get_stats()
        assert stats["scans_performed"] == 1
        assert stats["stocks_promoted"] == 3
    
    @pytest.mark.asyncio
    async def test_start_stop(self, monitor):
        """Test starting and stopping the monitor"""
        await monitor.start()
        assert monitor._running == True
        assert monitor._task is not None
        
        await monitor.stop()
        assert monitor._running == False
    
    def test_is_trading_hours(self, monitor):
        """Test trading hours detection"""
        # Note: This test depends on actual current time
        # In production, you might want to mock datetime.now()
        result = monitor._is_trading_hours()
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_force_scan(self, monitor, pool_manager):
        """Test force scan via API"""
        await monitor.force_scan()
        
        # Should have promoted stocks
        stocks = await pool_manager.get_all_dynamic_stocks()
        assert len(stocks) > 0


class TestPromotionIntegration:
    """Integration tests for promotion mechanism"""
    
    @pytest.mark.asyncio
    async def test_full_promotion_flow(self):
        """Test complete promotion flow from scan to pool inclusion"""
        # Create components
        pool = DynamicPoolManager(max_dynamic_size=10)
        
        # Mock RankingService
        mock_ranking = AsyncMock()
        mock_ranking.get_surge_rank.return_value = pd.DataFrame([
            {"代码": "000858", "名称": "五粮液", "涨幅": 6.0},
            {"代码": "002594", "名称": "比亚迪", "涨幅": 5.5},
        ])
        
        # Create monitor
        monitor = PromotionMonitor(
            dynamic_pool=pool,
            ranking_service=mock_ranking,
            scan_interval=60,
            top_n=5,
            ttl_minutes=30
        )
        
        # Run scan
        await monitor._scan_and_promote()
        
        # Verify promotion
        stocks = await pool.get_all_dynamic_stocks()
        assert "000858" in stocks
        assert "002594" in stocks
        
        # Verify stats
        stats = await pool.get_stats()
        assert stats["promoted_count"] == 2
        
        # Verify promoted stock details
        promoted_list = stats["promoted_list"]
        assert any(s["code"] == "000858" for s in promoted_list)

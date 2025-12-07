import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, time, timedelta
from src.core.scheduling.scheduler import AcquisitionScheduler, SystemState

class TestSchedulerIntegration:
    """测试调度器与连接池的集成"""
    
    @pytest.mark.asyncio
    async def test_scheduler_triggers_cooldown_and_warmup(self):
        """测试调度器在休眠和唤醒时触发冷却和预热"""
        
        # Mock connection_monitor
        with patch('src.core.monitoring.connection_monitor.connection_monitor') as mock_monitor:
            mock_monitor.cooldown_all = AsyncMock()
            mock_monitor.warmup_all = AsyncMock()
            
            # Mock calendar_service
            mock_calendar = MagicMock()
            mock_calendar.is_trading_day.return_value = True
            mock_calendar.get_next_trading_day.return_value = datetime(2025, 11, 30).date()
            
            scheduler = AcquisitionScheduler(mock_calendar)
            
            # Mock _get_next_start_time to return a time in the future
            # 这样 wait_seconds > 0，会触发休眠逻辑
            future_time = datetime.now() + timedelta(seconds=1)
            scheduler._get_next_start_time = MagicMock(return_value=future_time)
            
            # Mock asyncio.sleep to avoid waiting
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                await scheduler.wait_for_next_run()
                
                # 验证调用顺序
                # 1. 进入休眠前调用 cooldown
                mock_monitor.cooldown_all.assert_awaited_once()
                
                # 2. 调用 sleep
                mock_sleep.assert_awaited_once()
                
                # 3. 唤醒后调用 warmup
                mock_monitor.warmup_all.assert_awaited_once()
                
                # 验证状态
                assert scheduler.state == SystemState.RUNNING

    @pytest.mark.asyncio
    async def test_scheduler_no_wait_no_trigger(self):
        """测试无需等待时不触发冷却和预热"""
        
        with patch('src.core.monitoring.connection_monitor.connection_monitor') as mock_monitor:
            mock_monitor.cooldown_all = AsyncMock()
            mock_monitor.warmup_all = AsyncMock()
            
            scheduler = AcquisitionScheduler()
            
            # Mock _get_next_start_time to return a time in the past
            # 这样 wait_seconds <= 0
            past_time = datetime.now() - timedelta(seconds=1)
            scheduler._get_next_start_time = MagicMock(return_value=past_time)
            
            await scheduler.wait_for_next_run()
            
            # 验证不调用
            mock_monitor.cooldown_all.assert_not_awaited()
            mock_monitor.warmup_all.assert_not_awaited()

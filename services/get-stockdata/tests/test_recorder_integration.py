"""
集成测试：智能调度器 + 快照录制器
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime, time
from src.core.recorder.snapshot_recorder import SnapshotRecorder
from src.core.stock_pool.manager import StockPoolManager
from src.core.scheduling.scheduler import AcquisitionScheduler

# Mock Scheduler to control time
class MockScheduler(AcquisitionScheduler):
    def __init__(self, should_run=True):
        self.mock_should_run = should_run
        self.wait_called = False
        
    def should_run_now(self):
        return self.mock_should_run
        
    async def wait_for_next_run(self):
        self.wait_called = True
        # Simulate wait
        await asyncio.sleep(0.1)
        self.mock_should_run = True # After wait, allow run

@pytest.mark.asyncio
async def test_recorder_scheduling_integration():
    # Setup
    pool_manager = MagicMock(spec=StockPoolManager)
    pool_manager.get_pool_symbols.return_value = ['600000', '000001']
    
    recorder = SnapshotRecorder(pool_manager, storage_path="/tmp/test_integration")
    
    # Inject Mock Scheduler
    mock_scheduler = MockScheduler(should_run=False) # Start with False to test wait logic
    recorder.scheduler = mock_scheduler
    
    # Mock Mootdx Client
    mock_client = MagicMock()
    mock_client.quotes.return_value = None # Return None to skip processing logic
    
    with patch('mootdx.quotes.Quotes.factory', return_value=mock_client):
        # Run recorder for a short time
        recorder.is_running = True
        
        # Run start() in background task
        task = asyncio.create_task(recorder.start())
        
        # Let it run for a bit
        await asyncio.sleep(0.5)
        
        # Stop recorder
        recorder.is_running = False
        await task
        
        # Verify
        assert mock_scheduler.wait_called == True
        print("✅ Recorder correctly waited when scheduler said NO")

"""
自适应调度器单元测试

测试 AdaptiveKLineSyncScheduler 的各个功能模块
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytz

from core.adaptive_scheduler import (
    AdaptiveKLineSyncScheduler,
    CloudSyncFailedException,
    CloudSyncTimeoutException,
    DataVolumeAnomalyException
)

CST = pytz.timezone('Asia/Shanghai')


@pytest.fixture
def mock_mysql_pool():
    """Mock MySQL连接池"""
    pool = AsyncMock()
    conn = AsyncMock()
    cursor = AsyncMock()
    
    # 设置上下文管理器
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None
    
    conn.cursor.return_value.__aenter__.return_value = cursor
    conn.cursor.return_value.__aexit__.return_value = None
    
    return pool, cursor


@pytest.mark.asyncio
async def test_predict_wait_window_with_history(mock_mysql_pool):
    """测试历史预测逻辑 - 有历史记录"""
    pool, cursor = mock_mysql_pool
    
    # Mock返回前一交易日完成时间
    yesterday = datetime.now(CST) - timedelta(days=1)
    completion_time = yesterday.replace(hour=18, minute=55, second=0, microsecond=0)
    
    cursor.fetchone.return_value = {
        'updated_at': completion_time,
        'total_records': 5000
    }
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    target_window = await scheduler.predict_wait_window()
    
    # 验证目标窗口 = 今天的 18:50 (18:55 - 5分钟)
    assert target_window is not None
    assert target_window.hour == 18
    assert target_window.minute == 50


@pytest.mark.asyncio
async def test_predict_wait_window_no_history(mock_mysql_pool):
    """测试历史预测逻辑 - 无历史记录"""
    pool, cursor = mock_mysql_pool
    
    # Mock返回空结果
    cursor.fetchone.return_value = None
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    target_window = await scheduler.predict_wait_window()
    
    # 验证返回None
    assert target_window is None


@pytest.mark.asyncio
async def test_poll_for_signal_success(mock_mysql_pool):
    """测试信号检测成功场景"""
    pool, cursor = mock_mysql_pool
    
    # Mock返回 completed 状态
    cursor.fetchone.return_value = {
        'status': 'completed',
        'total_records': 5000,
        'updated_at': datetime.now(CST),
        'error_message': None
    }
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    
    # 使用较短的轮询间隔进行测试
    scheduler.poll_interval_min = 0.01  # 0.6秒
    
    completion_time, total_records = await scheduler.poll_for_signal()
    
    assert total_records == 5000
    assert completion_time is not None


@pytest.mark.asyncio
async def test_poll_for_signal_failed(mock_mysql_pool):
    """测试云端采集失败场景"""
    pool, cursor = mock_mysql_pool
    
    # Mock返回 failed 状态
    cursor.fetchone.return_value = {
        'status': 'failed',
        'total_records': 0,
        'updated_at': datetime.now(CST),
        'error_message': 'Baostock timeout'
    }
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    
    # 验证抛出 CloudSyncFailedException
    with pytest.raises(CloudSyncFailedException) as exc_info:
        await scheduler.poll_for_signal()
    
    assert 'Baostock timeout' in str(exc_info.value)


@pytest.mark.asyncio
async def test_poll_for_signal_timeout(mock_mysql_pool):
    """测试超时场景"""
    pool, cursor = mock_mysql_pool
    
    # Mock返回空结果（未发现今日记录）
    cursor.fetchone.return_value = None
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    
    # 设置超时时间为过去时间
    scheduler.timeout_time_str = "00:00"
    scheduler.poll_interval_min = 0.01
    
    # 验证抛出 CloudSyncTimeoutException
    with pytest.raises(CloudSyncTimeoutException):
        await scheduler.poll_for_signal()


@pytest.mark.asyncio
async def test_data_volume_anomaly(mock_mysql_pool):
    """测试数据量异常检测"""
    pool, cursor = mock_mysql_pool
    
    # Mock返回记录数过少的 completed 状态
    cursor.fetchone.return_value = {
        'status': 'completed',
        'total_records': 3000,  # < 4800
        'updated_at': datetime.now(CST),
        'error_message': None
    }
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    scheduler.min_records = 4800
    
    # 验证抛出 DataVolumeAnomalyException
    with pytest.raises(DataVolumeAnomalyException) as exc_info:
        await scheduler.poll_for_signal()
    
    assert '3000' in str(exc_info.value)
    assert '4800' in str(exc_info.value)


@pytest.mark.asyncio
async def test_adaptive_wait_skip_when_no_target(mock_mysql_pool):
    """测试智能等待 - 无目标时间时跳过"""
    pool, _ = mock_mysql_pool
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    
    # 无目标时间应该立即返回
    await scheduler.adaptive_wait(None)
    # 如果没有异常就是成功


@pytest.mark.asyncio
async def test_adaptive_wait_skip_when_past_target(mock_mysql_pool):
    """测试智能等待 - 已过目标时间时跳过"""
    pool, _ = mock_mysql_pool
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    
    # 目标时间为过去
    past_time = datetime.now(CST) - timedelta(hours=1)
    
    await scheduler.adaptive_wait(past_time)
    # 如果没有异常就是成功


@pytest.mark.asyncio
async def test_check_today_signal(mock_mysql_pool):
    """测试今日信号检查"""
    pool, cursor = mock_mysql_pool
    
    now = datetime.now(CST)
    cursor.fetchone.return_value = {
        'status': 'completed',
        'total_records': 5000,
        'updated_at': now,
        'error_message': None
    }
    
    scheduler = AdaptiveKLineSyncScheduler(pool)
    signal = await scheduler._check_today_signal()
    
    assert signal is not None
    assert signal['status'] == 'completed'
    assert signal['total_records'] == 5000
    # 验证时间已格式化为字符串
    assert isinstance(signal['updated_at'], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

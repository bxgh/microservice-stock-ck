# -*- coding: utf-8 -*-
"""
HistoryService 单元测试

测试历史K线服务的核心功能。

@author: EPIC-007 Story 007.04
@date: 2025-12-07
"""

import pytest
import pandas as pd
from datetime import datetime

from src.data_services import HistoryService, AdjustType, Frequency


class TestHistoryServiceBasic:
    """基础功能测试"""
    
    def test_import(self):
        """测试导入"""
        assert HistoryService is not None
        assert AdjustType.FORWARD.value == "2"
        assert AdjustType.BACKWARD.value == "1"
        assert AdjustType.NONE.value == "3"
    
    def test_frequency_enum(self):
        """测试周期枚举"""
        assert Frequency.DAILY.value == "d"
        assert Frequency.WEEKLY.value == "w"
        assert Frequency.MONTHLY.value == "m"
        assert Frequency.MIN_5.value == "5"
        assert Frequency.MIN_15.value == "15"
        assert Frequency.MIN_30.value == "30"
        assert Frequency.MIN_60.value == "60"
    
    def test_standard_fields(self):
        """测试标准字段"""
        expected = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                    'pct_change', 'turnover', 'pe', 'pb']
        assert HistoryService.STANDARD_FIELDS == expected


@pytest.mark.asyncio
class TestHistoryService:
    """HistoryService 测试"""
    
    async def test_initialization(self):
        """测试服务初始化"""
        service = HistoryService(enable_cache=False)
        
        success = await service.initialize()
        assert success is True
        
        await service.close()
    
    async def test_get_daily_with_mock(self, monkeypatch):
        """测试日线获取（使用模拟数据）"""
        from src.data_sources.providers import DataResult
        
        mock_data = pd.DataFrame({
            'date': ['2024-12-01', '2024-12-02', '2024-12-03'],
            'open': [100.0, 101.0, 102.0],
            'high': [102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0],
            'close': [101.0, 102.0, 103.0],
            'volume': [1000, 1100, 1200],
            'amount': [100000, 111000, 122000],
            'pctChg': [1.0, 0.99, 0.98],
            'turn': [0.1, 0.11, 0.12],
            'peTTM': [20.0, 20.2, 20.4],
            'pbMRQ': [3.0, 3.1, 3.2],
        })
        
        async def mock_fetch_from_baostock(*args, **kwargs):
            return mock_data
        
        service = HistoryService(enable_cache=False)
        await service.initialize()
        
        # 替换方法
        monkeypatch.setattr(service, '_fetch_from_baostock', mock_fetch_from_baostock)
        
        # 测试获取日线
        result = await service.get_daily('600519', '2024-12-01', '2024-12-03')
        
        # 验证
        assert not result.empty
        assert len(result) == 3
        assert 'pct_change' in result.columns
        assert 'turnover' in result.columns
        assert 'pe' in result.columns
        assert 'pb' in result.columns
        
        await service.close()
    
    async def test_stats(self, monkeypatch):
        """测试统计信息"""
        mock_data = pd.DataFrame({
            'date': ['2024-12-01'],
            'open': [100.0],
            'close': [101.0],
            'high': [102.0],
            'low': [99.0],
            'volume': [1000],
            'amount': [100000],
        })
        
        async def mock_fetch(*args, **kwargs):
            return mock_data
        
        service = HistoryService(enable_cache=False)
        await service.initialize()
        
        monkeypatch.setattr(service, '_fetch_from_baostock', mock_fetch)
        
        # 调用一次
        await service.get_daily('600519', '2024-12-01', '2024-12-01')
        
        stats = service.get_stats()
        
        assert stats['total_requests'] == 1
        assert stats['baostock_calls'] == 1
        
        await service.close()
    
    async def test_input_validation(self):
        """测试输入验证"""
        service = HistoryService(enable_cache=False)
        await service.initialize()
        
        # 空代码
        with pytest.raises(ValueError, match="code cannot be empty"):
            await service.get_daily('', '2024-12-01', '2024-12-03')
        
        # 空日期
        with pytest.raises(ValueError, match="start_date and end_date cannot be empty"):
            await service.get_daily('600519', '', '2024-12-03')
        
        await service.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

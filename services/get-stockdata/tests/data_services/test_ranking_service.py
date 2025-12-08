# -*- coding: utf-8 -*-
"""
RankingService 单元测试

测试榜单数据服务的核心功能。

@author: P0 Task - Missing Tests
@date: 2025-12-08
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.data_services import RankingService
from src.data_services.schemas import AnomalyType
from src.data_sources.providers import DataResult


class TestRankingServiceBasic:
    """基础功能测试"""
    
    def test_import(self):
        """测试导入"""
        assert RankingService is not None
        assert AnomalyType is not None
    
    def test_anomaly_types(self):
        """测试异动类型枚举"""
        # 验证部分关键类型
        assert AnomalyType.ROCKET_LAUNCH.value == "火箭发射"
        assert AnomalyType.LARGE_BUY.value == "大笔买入"
        assert AnomalyType.LIMIT_UP_SEALED.value == "封涨停板"
    
    def test_initialization_params(self):
        """测试初始化参数"""
        # 默认启用缓存
        service = RankingService()
        assert service._enable_cache is True
        
        # 禁用缓存
        service_no_cache = RankingService(enable_cache=False)
        assert service_no_cache._enable_cache is False


@pytest.mark.asyncio
class TestRankingService:
    """RankingService 功能测试"""
    
    async def test_initialization(self):
        """测试服务初始化"""
        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.initialize = AsyncMock(return_value=True)
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        
        success = await service.initialize()
        assert success is True
        
        await service.close()
    
    async def test_get_hot_rank(self, monkeypatch):
        """测试人气榜查询"""
        mock_data = pd.DataFrame({
            'rank': [1, 2, 3],
            'code': ['000001', '600519', '000858'],
            'name': ['平安银行', '贵州茅台', '五粮液'],
            'change_pct': [5.2, 3.8, 4.5],
            'latest_price': [10.5, 1800.0, 150.0],
            'volume': [1000000, 50000, 80000],
            'amount': [10500000, 90000000, 12000000],
        })
        
        mock_data_service = AsyncMock()
        mock_data_service.get_ranking = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        await service.initialize()
        
        # 测试获取人气榜
        items = await service.get_hot_rank(limit=10)
        
        assert len(items) == 3
        assert items[0].code == '000001'
        assert items[0].name == '平安银行'
        
        await service.close()
    
    async def test_get_limit_up_stocks(self, monkeypatch):
        """测试涨停池查询"""
        mock_data = pd.DataFrame({
            'code': ['000001', '600519'],
            'name': ['涨停股1', '涨停股2'],
            'change_pct': [10.0, 9.99],
            'limit_up_time': ['09:30:00', '09:31:00'],
            'continuous_days': [1, 2],
        })
        
        mock_data_service = AsyncMock()
        mock_data_service.get_ranking = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        await service.initialize()
        
        # 测试涨停池
        items = await service.get_limit_up_pool()
        
        assert len(items) == 2
        assert items[0].code == '000001'
        
        await service.close()
    
    async def test_get_anomaly_stocks(self, monkeypatch):
        """测试盘口异动查询"""
        mock_data = pd.DataFrame({
            'code': ['000001'],
            'name': ['异动股票'],
            'change_pct': [8.5],
            'latest_price': [15.0],
        })
        
        mock_data_service = AsyncMock()
        mock_data_service.get_ranking = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        await service.initialize()
        
        # 测试异动查询
        items = await service.get_anomaly_stocks(
            anomaly_type=AnomalyType.ROCKET_LAUNCH,
            limit=50
        )
        
        assert len(items) == 1
        assert items[0].code == '000001'
        
        # 验证调用参数
        mock_data_service.get_ranking.assert_called_with(
            ranking_type='anomaly',
            symbol='火箭发射',
            limit=50
        )
        
        await service.close()
    
    async def test_query_anomaly_custom(self, monkeypatch):
        """测试自定义异动查询"""
        mock_data = pd.DataFrame({
            'code': ['000001', '600519'],
            'name': ['股票1', '股票2'],
            'change_pct': [5.0, 6.0],
        })
        
        mock_data_service = AsyncMock()
        mock_data_service.screen = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='pywencai'
        ))
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        await service.initialize()
        
        # 测试自然语言查询
        items = await service.query_anomaly("涨幅大于3%且换手率大于20%", limit=100)
        
        assert len(items) == 2
        assert items[0].code == '000001'
        
        # 验证调用了screen方法
        mock_data_service.screen.assert_called_with(
            query="涨幅大于3%且换手率大于20%",
            perpage=100
        )
        
        await service.close()
    
    async def test_advanced_screening(self, monkeypatch):
        """测试高级筛选"""
        mock_data = pd.DataFrame({
            'code': ['000001'],
            'name': ['筛选结果'],
        })
        
        mock_data_service = AsyncMock()
        mock_data_service.screen = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='pywencai'
        ))
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        await service.initialize()
        
        # 测试高级筛选
        conditions = {
            'change_pct_min': 3.0,
            'turnover_rate_min': 10.0,
        }
        items = await service.advanced_screening(conditions, limit=50)
        
        assert len(items) == 1
        
        # 验证生成的查询字符串
        call_args = mock_data_service.screen.call_args
        query = call_args.kwargs['query']
        assert '涨幅大于3.0%' in query
        assert '换手率大于10.0%' in query
        
        await service.close()
    
    async def test_failed_request_handling(self, monkeypatch):
        """测试失败请求处理"""
        mock_data_service = AsyncMock()
        mock_data_service.get_ranking = AsyncMock(return_value=DataResult(
            success=False,
            data=None,
            error="Provider unavailable"
        ))
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        await service.initialize()
        
        # 失败时应返回空列表
        items = await service.get_hot_rank()
        
        assert items == []
        
        await service.close()
    
    async def test_field_standardization(self, monkeypatch):
        """测试字段标准化"""
        # 测试code补零
        mock_data = pd.DataFrame({
            'rank': [1],
            'code': ['1'],  # 不足6位
            'name': ['测试股票'],
        })
        
        mock_data_service = AsyncMock()
        mock_data_service.get_ranking = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        await service.initialize()
        
        items = await service.get_hot_rank()
        
        # 验证code已补零
        assert items[0].code == '000001'
        
        await service.close()
    
    async def test_continuous_limit_up_sorting(self, monkeypatch):
        """测试连板排序"""
        mock_data = pd.DataFrame({
            'code': ['000001', '600519', '000858'],
            'name': ['股票1', '股票2', '股票3'],
            'continuous_days': [2, 5, 3],  # 乱序
        })
        
        mock_data_service = AsyncMock()
        mock_data_service.get_ranking = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = RankingService(
            enable_cache=False,
            data_service=mock_data_service
        )
        await service.initialize()
        
        items = await service.get_continuous_limit_up()
        
        # 应按连板天数降序排序
        assert len(items) == 3
        assert items[0].continuous_days >= items[1].continuous_days
        assert items[1].continuous_days >= items[2].continuous_days
        
        await service.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

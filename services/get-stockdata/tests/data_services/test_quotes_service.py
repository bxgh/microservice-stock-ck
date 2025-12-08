# -*- coding: utf-8 -*-
"""
QuotesService 单元测试

测试实时行情服务的核心功能。

@author: P0 Task - Missing Tests
@date: 2025-12-08
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock

from src.data_services import QuotesService
from src.data_sources.providers import DataResult


class TestQuotesServiceBasic:
    """基础功能测试"""
    
    def test_import(self):
        """测试导入"""
        assert QuotesService is not None
    
    def test_initialization_params(self):
        """测试初始化参数"""
        # 默认参数
        service = QuotesService()
        assert service._enable_cache is True
        assert service._initialized is False
        
        # 禁用缓存
        service_no_cache = QuotesService(enable_cache=False)
        assert service_no_cache._enable_cache is False
    
    def test_stats_structure(self):
        """测试统计信息结构"""
        service = QuotesService()
        stats = service.get_stats()
        
        assert 'total_requests' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'provider_calls' in stats
        assert 'failed_requests' in stats
        assert 'cache_hit_rate' in stats


@pytest.mark.asyncio
class TestQuotesService:
    """QuotesService 功能测试"""
    
    async def test_initialization(self):
        """测试服务初始化"""
        service = QuotesService(enable_cache=False)
        
        success = await service.initialize()
        assert success is True
        assert service._initialized is True
        
        await service.close()
    
    async def test_get_quotes_with_mock(self, monkeypatch):
        """测试获取行情（使用模拟数据）"""
        mock_data = pd.DataFrame({
            'code': ['000001', '600519'],
            'name': ['平安银行', '贵州茅台'],
            'price': [10.5, 1800.0],
            'open': [10.3, 1790.0],
            'high': [10.6, 1820.0],
            'low': [10.2, 1785.0],
            'close': [10.5, 1800.0],
            'volume': [1000000, 50000],
            'amount': [10500000, 90000000],
            'change': [0.2, 10.0],
            'change_pct': [1.94, 0.56],
        })
        
        # Mock DataServiceManager
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock(return_value=True)
        mock_manager.close = AsyncMock()
        mock_manager.get_quotes = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock',
            latency_ms=100
        ))
        
        service = QuotesService(
            data_manager=mock_manager,
            enable_cache=False
        )
        await service.initialize()
        
        # 测试获取行情
        result = await service.get_quotes(['000001', '600519'])
        
        # 验证
        assert not result.empty
        assert len(result) == 2
        assert 'code' in result.columns
        assert 'name' in result.columns
        assert 'price' in result.columns
        assert result.iloc[0]['code'] == '000001'
        
        await service.close()
    
    async def test_get_quote_single(self, monkeypatch):
        """测试获取单个股票行情"""
        mock_data = pd.DataFrame({
            'code': ['000001'],
            'name': ['平安银行'],
            'price': [10.5],
            'change_pct': [1.94],
        })
        
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock(return_value=True)
        mock_manager.close = AsyncMock()
        mock_manager.get_quotes = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = QuotesService(
            data_manager=mock_manager,
            enable_cache=False
        )
        await service.initialize()
        
        # 测试单个查询
        quote = await service.get_quote('000001')
        
        assert quote is not None
        assert quote['code'] == '000001'
        assert quote['name'] == '平安银行'
        
        await service.close()
    
    async def test_get_quotes_dict(self, monkeypatch):
        """测试获取字典格式行情"""
        mock_data = pd.DataFrame({
            'code': ['000001', '600519'],
            'name': ['平安银行', '贵州茅台'],
            'price': [10.5, 1800.0],
        })
        
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock(return_value=True)
        mock_manager.close = AsyncMock()
        mock_manager.get_quotes = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = QuotesService(
            data_manager=mock_manager,
            enable_cache=False
        )
        await service.initialize()
        
        # 测试字典格式
        result = await service.get_quotes_dict(['000001', '600519'])
        
        assert isinstance(result, dict)
        assert '000001' in result
        assert '600519' in result
        assert result['000001']['name'] == '平安银行'
        
        await service.close()
    
    async def test_input_validation(self):
        """测试输入验证"""
        service = QuotesService(enable_cache=False)
        await service.initialize()
        
        # 空代码列表
        with pytest.raises(ValueError, match="codes cannot be empty"):
            await service.get_quotes([])
        
        await service.close()
    
    async def test_stats_tracking(self, monkeypatch):
        """测试统计信息更新"""
        mock_data = pd.DataFrame({
            'code': ['000001'],
            'price': [10.5],
        })
        
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock(return_value=True)
        mock_manager.close = AsyncMock()
        mock_manager.get_quotes = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = QuotesService(
            data_manager=mock_manager,
            enable_cache=False
        )
        await service.initialize()
        
        # 调用一次
        await service.get_quotes(['000001'])
        
        stats = service.get_stats()
        
        assert stats['total_requests'] == 1
        assert stats['provider_calls'] == 1
        
        await service.close()
    
    async def test_failed_request_handling(self, monkeypatch):
        """测试失败请求处理"""
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock(return_value=True)
        mock_manager.close = AsyncMock()
        mock_manager.get_quotes = AsyncMock(return_value=DataResult(
            success=False,
            data=pd.DataFrame(),
            error="Provider not available"
        ))
        
        service = QuotesService(
            data_manager=mock_manager,
            enable_cache=False
        )
        await service.initialize()
        
        # 应该抛出RuntimeError
        with pytest.raises(RuntimeError, match="Failed to get quotes"):
            await service.get_quotes(['000001'])
        
        # 检查统计
        stats = service.get_stats()
        assert stats['failed_requests'] == 1
        
        await service.close()
    
    async def test_field_standardization(self, monkeypatch):
        """测试字段标准化"""
        # 测试code补零
        mock_data = pd.DataFrame({
            'code': ['1', '519'],  # 不足6位
            'name': ['测试1', '测试2'],
            'price': [10.0, 20.0],
        })
        
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock(return_value=True)
        mock_manager.close = AsyncMock()
        mock_manager.get_quotes = AsyncMock(return_value=DataResult(
            success=True,
            data=mock_data,
            provider='mock'
        ))
        
        service = QuotesService(
            data_manager=mock_manager,
            enable_cache=False
        )
        await service.initialize()
        
        result = await service.get_quotes(['000001', '600519'])
        
        # 验证code已补零
        assert result.iloc[0]['code'] == '000001'
        assert result.iloc[1]['code'] == '000519'
        
        await service.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

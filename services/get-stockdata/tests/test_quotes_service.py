#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuotesService 单元测试

使用 Mock Provider 测试 QuotesService 的核心功能：
- 正常查询流程
- 缓存机制
- 数据源降级
- 并发安全
- 异常处理

@author: EPIC-007 Story 007.02b
@date: 2025-12-06
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from src.data_services import QuotesService, CacheManager
from src.data_sources.providers import DataServiceManager, DataResult, DataType


@pytest_asyncio.fixture
async def mock_data_manager():
    """Mock DataServiceManager"""
    manager = AsyncMock(spec=DataServiceManager)
    manager.initialize = AsyncMock(return_value=True)
    manager.close = AsyncMock()
    return manager


@pytest_asyncio.fixture
async def mock_cache_manager():
    """Mock CacheManager"""
    cache = AsyncMock(spec=CacheManager)
    cache.initialize = AsyncMock(return_value=True)
    cache.close = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.generate_hash_key = MagicMock(return_value="test_hash")
    return cache


@pytest_asyncio.fixture
async def quotes_service(mock_data_manager, mock_cache_manager):
    """创建测试用 QuotesService"""
    service = QuotesService(
        data_manager=mock_data_manager,
        cache_manager=mock_cache_manager,
        enable_cache=True
    )
    await service.initialize()
    yield service
    await service.close()


def create_mock_dataframe(codes):
    """创建 Mock DataFrame"""
    return pd.DataFrame({
        'code': codes,
        'name': [f'Stock_{code}' for code in codes],
        'price': [10.0 + i for i in range(len(codes))],
        'open': [9.5 + i for i in range(len(codes))],
        'high': [10.5 + i for i in range(len(codes))],
        'low': [9.0 + i for i in range(len(codes))],
        'close': [10.0 + i for i in range(len(codes))],
        'pre_close': [9.8 + i for i in range(len(codes))],
        'volume': [100000 + i * 1000 for i in range(len(codes))],
        'amount': [1000000 + i * 10000 for i in range(len(codes))],
        'change': [0.2 + i * 0.1 for i in range(len(codes))],
        'change_pct': [2.0 + i * 0.5 for i in range(len(codes))],
    })


class TestQuotesServiceBasic:
    """基础功能测试"""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_data_manager, mock_cache_manager):
        """测试初始化成功"""
        service = QuotesService(
            data_manager=mock_data_manager,
            cache_manager=mock_cache_manager
        )
        
        result = await service.initialize()
        
        assert result is True
        mock_data_manager.initialize.assert_called_once()
        mock_cache_manager.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_quotes_success(self, quotes_service, mock_data_manager):
        """测试正常获取行情"""
        codes = ['000001', '600519']
        mock_df = create_mock_dataframe(codes)
        
        mock_result = DataResult(
            success=True,
            data=mock_df,
            provider='mootdx',
            data_type=DataType.QUOTES
        )
        mock_data_manager.get_quotes = AsyncMock(return_value=mock_result)
        
        result = await quotes_service.get_quotes(codes)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'code' in result.columns
        assert 'price' in result.columns
        mock_data_manager.get_quotes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_quote_single(self, quotes_service, mock_data_manager):
        """测试单个股票查询"""
        code = '000001'
        mock_df = create_mock_dataframe([code])
        
        mock_result = DataResult(
            success=True,
            data=mock_df,
            provider='mootdx'
        )
        mock_data_manager.get_quotes = AsyncMock(return_value=mock_result)
        
        result = await quotes_service.get_quote(code)
        
        assert result is not None
        assert isinstance(result, pd.Series)
        assert result['code'] == code
    
    @pytest.mark.asyncio
    async def test_get_quotes_empty_codes(self, quotes_service):
        """测试空代码列表"""
        with pytest.raises(ValueError, match="codes cannot be empty"):
            await quotes_service.get_quotes([])


class TestQuotesServiceCache:
    """缓存机制测试"""
    
    @pytest.mark.asyncio
    async def test_cache_miss_then_set(self, quotes_service, mock_data_manager, mock_cache_manager):
        """测试缓存未命中，然后设置缓存"""
        codes = ['000001']
        mock_df = create_mock_dataframe(codes)
        
        # 模拟缓存未命中
        mock_cache_manager.get = AsyncMock(return_value=None)
        
        mock_result = DataResult(success=True, data=mock_df, provider='mootdx')
        mock_data_manager.get_quotes = AsyncMock(return_value=mock_result)
        
        result = await quotes_service.get_quotes(codes)
        
        # 验证从 provider 获取数据
        mock_data_manager.get_quotes.assert_called_once()
        # 验证设置缓存
        mock_cache_manager.set.assert_called_once()
        
        stats = quotes_service.get_stats()
        assert stats['cache_misses'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, quotes_service, mock_data_manager, mock_cache_manager):
        """测试缓存命中"""
        codes = ['000001']
        mock_df = create_mock_dataframe(codes)
        
        # 模拟缓存命中
        mock_cache_manager.get = AsyncMock(return_value=mock_df)
        
        result = await quotes_service.get_quotes(codes)
        
        # 验证未调用 provider
        mock_data_manager.get_quotes.assert_not_called()
        
        stats = quotes_service.get_stats()
        assert stats['cache_hits'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_disabled(self, mock_data_manager):
        """测试禁用缓存"""
        service = QuotesService(
            data_manager=mock_data_manager,
            enable_cache=False
        )
        await service.initialize()
        
        codes = ['000001']
        mock_df = create_mock_dataframe(codes)
        mock_result = DataResult(success=True, data=mock_df, provider='mootdx')
        mock_data_manager.get_quotes = AsyncMock(return_value=mock_result)
        
        result = await service.get_quotes(codes, use_cache=True)
        
        # 即使 use_cache=True，也会调用 provider（因为缓存被禁用）
        mock_data_manager.get_quotes.assert_called_once()


class TestQuotesServiceFallback:
    """数据源降级测试"""
    
    @pytest.mark.asyncio
    async def test_provider_failure(self, quotes_service, mock_data_manager):
        """测试数据源失败抛出异常"""
        codes = ['000001']
        
        mock_result = DataResult(
            success=False,
            error="Connection failed",
            provider='mootdx'
        )
        mock_data_manager.get_quotes = AsyncMock(return_value=mock_result)
        
        with pytest.raises(RuntimeError, match="Failed to get quotes"):
            await quotes_service.get_quotes(codes)
        
        stats = quotes_service.get_stats()
        assert stats['failed_requests'] == 1


class TestQuotesServiceFiltering:
    """筛选功能测试"""
    
    @pytest.mark.asyncio
    async def test_get_limit_up_stocks(self, quotes_service, mock_data_manager):
        """测试涨停股票筛选"""
        # 创建包含涨停股的数据
        mock_df = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['Stock1', 'Stock2', 'Stock3'],
            'price': [10.0, 11.0, 12.0],
            'change_pct': [9.95, 5.0, 10.1],  # 第1和第3只涨停
            'open': [9.0, 10.0, 11.0],
            'high': [10.0, 11.0, 12.0],
            'low': [9.0, 10.0, 11.0],
            'close': [10.0, 11.0, 12.0],
            'pre_close': [9.0, 10.0, 11.0],
            'volume': [100000, 200000, 300000],
            'amount': [1000000, 2000000, 3000000],
            'change': [1.0, 0.5, 1.1],
        })
        
        mock_result = DataResult(success=True, data=mock_df, provider='easyquotation')
        mock_data_manager.get_quotes = AsyncMock(return_value=mock_result)
        
        result = await quotes_service.get_limit_up_stocks()
        
        assert len(result) == 2
        assert '000001' in result['code'].values
        assert '000003' in result['code'].values


class TestQuotesServiceConcurrency:
    """并发安全测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_initialize(self, mock_data_manager, mock_cache_manager):
        """测试并发初始化安全性"""
        service = QuotesService(
            data_manager=mock_data_manager,
            cache_manager=mock_cache_manager
        )
        
        # 并发调用 initialize
        results = await asyncio.gather(
            service.initialize(),
            service.initialize(),
            service.initialize()
        )
        
        # 所有调用都应该成功
        assert all(results)
        # 但实际只初始化一次
        assert mock_data_manager.initialize.call_count == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, quotes_service, mock_data_manager):
        """测试并发请求"""
        codes = ['000001', '000002']
        mock_df = create_mock_dataframe(codes)
        mock_result = DataResult(success=True, data=mock_df, provider='mootdx')
        mock_data_manager.get_quotes = AsyncMock(return_value=mock_result)
        
        # 并发请求
        results = await asyncio.gather(
            quotes_service.get_quotes(codes),
            quotes_service.get_quotes(codes),
            quotes_service.get_quotes(codes)
        )
        
        # 所有请求都应该成功
        assert len(results) == 3
        for result in results:
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2


class TestQuotesServiceStats:
    """统计功能测试"""
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, quotes_service, mock_data_manager, mock_cache_manager):
        """测试统计信息跟踪"""
        codes = ['000001']
        mock_df = create_mock_dataframe(codes)
        mock_result = DataResult(success=True, data=mock_df, provider='mootdx')
        
        # 第一次请求 - 缓存未命中
        mock_cache_manager.get = AsyncMock(return_value=None)
        mock_data_manager.get_quotes = AsyncMock(return_value=mock_result)
        await quotes_service.get_quotes(codes)
        
        # 第二次请求 - 缓存命中
        mock_cache_manager.get = AsyncMock(return_value=mock_df)
        await quotes_service.get_quotes(codes)
        
        stats = quotes_service.get_stats()
        
        assert stats['total_requests'] == 2
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['provider_calls'] == 1
        assert 'cache_hit_rate' in stats
        assert stats['cache_hit_rate'] == '50.0%'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

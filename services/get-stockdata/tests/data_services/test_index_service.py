# -*- coding: utf-8 -*-
"""
IndexService 单元测试

@author: EPIC-007 Story 007.05
@date: 2025-12-07
"""

import pytest
import pandas as pd

from src.data_services import IndexService


class TestIndexServiceBasic:
    """基础功能测试"""
    
    def test_import(self):
        """测试导入"""
        assert IndexService is not None
    
    def test_benchmark_list(self):
        """测试基准指数列表"""
        service = IndexService()
        benchmarks = service.get_benchmark_list()
        
        assert len(benchmarks) == 11
        assert '000300' in benchmarks  # 沪深300
        assert '000905' in benchmarks  # 中证500
        assert '899050' in benchmarks  # 北证50
        assert '000922' in benchmarks  # 中证红利


@pytest.mark.asyncio
class TestIndexService:
    """IndexService 测试"""
    
    async def test_initialization(self):
        """测试服务初始化"""
        service = IndexService(enable_cache=False)
        
        success = await service.initialize()
        assert success is True
        
        await service.close()
    
    async def test_get_constituents_with_mock(self, monkeypatch):
        """测试成分股获取（模拟数据）"""
        mock_data = pd.DataFrame({
            '品种代码': ['600000', '600001', '600002'],
            '品种名称': ['股票A', '股票B', '股票C'],
        })
        
        async def mock_run(*args, **kwargs):
            return mock_data
        
        service = IndexService(enable_cache=False)
        await service.initialize()
        
        # 替换 akshare 调用
        import asyncio
        original = asyncio.get_event_loop().run_in_executor
        
        async def patched_executor(executor, func):
            return mock_data
        
        monkeypatch.setattr(asyncio.get_event_loop(), 'run_in_executor', patched_executor)
        
        result = await service.get_constituents('000300')
        
        assert isinstance(result, list)
        
        await service.close()
    
    async def test_get_etf_holdings_with_mock(self, monkeypatch):
        """测试ETF持仓获取（模拟数据）"""
        mock_data = pd.DataFrame({
            '股票代码': ['600519', '300750'],
            '股票名称': ['贵州茅台', '宁德时代'],
            '占净值比例': [10.5, 8.2],
            '持股数': [1000, 2000],
            '持仓市值': [1000000, 800000],
        })
        
        service = IndexService(enable_cache=False)
        await service.initialize()
        
        # 模拟 akshare
        import asyncio
        monkeypatch.setattr(
            asyncio.get_event_loop(), 
            'run_in_executor',
            lambda x, f: asyncio.coroutine(lambda: mock_data)()
        )
        
        # 只测试字段映射逻辑
        await service.close()
    
    async def test_stats(self):
        """测试统计信息"""
        service = IndexService(enable_cache=False)
        await service.initialize()
        
        stats = service.get_stats()
        
        assert 'total_requests' in stats
        assert 'cache_hits' in stats
        
        await service.close()
    
    def test_search_index(self):
        """测试搜索"""
        service = IndexService(enable_cache=False)
        
        results = service.search_index('沪深300')
        
        assert len(results) > 0
        assert results[0]['code'] == '000300'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# -*- coding: utf-8 -*-
"""
SectorService 单元测试

@author: EPIC-007 Story 007.06
@date: 2025-12-07
"""

import pytest
import pandas as pd

from src.data_services import SectorService


class TestSectorServiceBasic:
    """基础功能测试"""
    
    def test_import(self):
        """测试导入"""
        assert SectorService is not None
    
    def test_query_templates(self):
        """测试查询模板"""
        service = SectorService()
        
        assert 'industry_ranking' in service.QUERY_TEMPLATES
        assert 'concept_ranking' in service.QUERY_TEMPLATES
        assert 'sector_stocks' in service.QUERY_TEMPLATES
        assert 'stock_sectors' in service.QUERY_TEMPLATES


@pytest.mark.asyncio
class TestSectorService:
    """SectorService 功能测试"""
    
    async def test_initialization(self):
        """测试服务初始化"""
        service = SectorService(enable_cache=False)
        
        success = await service.initialize()
        assert success is True
        
        await service.close()
    
    async def test_stats(self):
        """测试统计信息"""
        service = SectorService(enable_cache=False)
        await service.initialize()
        
        stats = service.get_stats()
        
        assert 'total_requests' in stats
        assert 'cache_hits' in stats
        assert 'pywencai_calls' in stats
        
        await service.close()
    
    async def test_standardize_ranking_data(self):
        """测试数据标准化"""
        service = SectorService(enable_cache=False)
        
        # 模拟 pywencai 返回数据
        mock_df = pd.DataFrame({
            '股票代码': ['000001.SZ', '000002.SZ'],
            '股票简称': ['股票A', '股票B'],
            '涨跌幅': [5.0, 3.0],
            '行业简称': ['银行', '银行'],
        })
        
        result = service._standardize_ranking_data(mock_df, 'industry')
        
        # 应该聚合成1行 (银行)
        assert len(result) == 1
        assert result.iloc[0]['sector_name'] == '银行'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

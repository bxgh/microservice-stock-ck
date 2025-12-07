# -*- coding: utf-8 -*-
"""
FinancialService 单元测试

@author: EPIC-007 Story 007.08
@date: 2025-12-07
"""

import pytest
from src.data_services import FinancialService


class TestFinancialServiceBasic:
    """基础功能测试"""
    
    def test_import(self):
        """测试导入"""
        assert FinancialService is not None
    
    def test_instantiation(self):
        """测试实例化"""
        service = FinancialService(enable_cache=False)
        assert service is not None


@pytest.mark.asyncio
class TestFinancialService:
    """FinancialService 功能测试"""
    
    async def test_initialization(self):
        """测试服务初始化"""
        service = FinancialService(enable_cache=False)
        
        success = await service.initialize()
        assert success is True
        
        await service.close()
    
    async def test_stats(self):
        """测试统计信息"""
        service = FinancialService(enable_cache=False)
        await service.initialize()
        
        stats = service.get_stats()
        
        assert 'total_requests' in stats
        assert 'cache_hits' in stats
        assert 'akshare_calls' in stats
        
        await service.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

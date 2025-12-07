# -*- coding: utf-8 -*-
"""
FundFlowService 单元测试

@author: EPIC-007 Story 007.09
@date: 2025-12-07
"""

import pytest
import pandas as pd
from src.data_services import FundFlowService


class TestFundFlowServiceBasic:
    """基础功能测试"""
    
    def test_import(self):
        """测试导入"""
        assert FundFlowService is not None
    
    def test_instantiation(self):
        """测试实例化"""
        service = FundFlowService(enable_cache=False)
        assert service is not None
    
    def test_thresholds(self):
        """测试阈值配置"""
        service = FundFlowService()
        assert service.LARGE_THRESHOLD == 1000000
        assert service.MEDIUM_THRESHOLD == 100000


@pytest.mark.asyncio
class TestFundFlowService:
    """FundFlowService 功能测试"""
    
    async def test_empty_result(self):
        """测试空结果"""
        service = FundFlowService(enable_cache=False)
        
        result = service._empty_result('600519', '2025-12-07')
        
        assert result['code'] == '600519'
        assert result['large_net'] == 0.0
        assert result['total_net'] == 0.0
    
    async def test_calculate_fund_flow(self):
        """测试资金流向计算"""
        service = FundFlowService(enable_cache=False)
        
        # 模拟分笔数据
        df = pd.DataFrame({
            'amount': [1500000, 500000, 50000],  # 大单、中单、小单
            'direction': ['B', 'S', 'B'],  # 买、卖、买
        })
        
        result = service._calculate_fund_flow(df, '600519', '2025-12-07')
        
        assert result['large_buy'] == 1500000
        assert result['medium_sell'] == 500000
        assert result['small_buy'] == 50000
        assert result['large_net'] == 1500000
        assert result['medium_net'] == -500000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

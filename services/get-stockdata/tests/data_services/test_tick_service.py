# -*- coding: utf-8 -*-
"""
TickService 单元测试

测试分笔成交服务的核心功能。

@author: EPIC-007 Story 007.02b
@date: 2025-12-07
"""

import pytest
import pandas as pd
from datetime import datetime

from src.data_services import TickService, TickAnalyzer, CapitalFlowResult


class TestTickAnalyzer:
    """测试 TickAnalyzer 分析器"""
    
    def test_calculate_direction(self):
        """测试买卖方向判断"""
        # 模拟分笔数据
        df = pd.DataFrame({
            'code': ['000001'] * 5,
            'time': ['09:30:00', '09:30:10', '09:30:20', '09:30:30', '09:30:40'],
            'price': [10.00, 10.05, 10.03, 10.03, 10.08],
            'volume': [100, 200, 150, 100, 300],
            'amount': [1000, 2010, 1504.5, 1003, 3024],
            'tick_type': [0, 0, 1, 0, 0],
        })
        
        # 计算方向
        result = TickAnalyzer.calculate_direction(df)
        
        # 验证
        assert 'direction' in result.columns
        assert result.loc[0, 'direction'] == 'N'  # 第一笔中性
        assert result.loc[1, 'direction'] == 'B'  # 价格上涨
        assert result.loc[2, 'direction'] == 'S'  # 价格下跌
        assert result.loc[3, 'direction'] == 'B'  # 平盘，tick_type=0（买盘）
        assert result.loc[4, 'direction'] == 'B'  # 价格上涨
    
    def test_identify_large_orders(self):
        """测试大单识别"""
        df = pd.DataFrame({
            'code': ['000001'] * 5,
            'time': ['09:30:00', '09:30:10', '09:30:20', '09:30:30', '09:30:40'],
            'price': [10.00] * 5,
            'volume': [100, 200, 5000, 10000, 15000],
            'amount': [1000, 2000, 500_000, 1_000_000, 1_500_000],
            'direction': ['B', 'B', 'B', 'S', 'B'],
        })
        
        # 识别50万以上大单
        large_orders = TickAnalyzer.identify_large_orders(df, threshold=500_000)
        
        # 验证
        assert len(large_orders) == 3
        assert 'order_level' in large_orders.columns
        
        # 只筛选买入大单
        buy_large_orders = TickAnalyzer.identify_large_orders(df, threshold=500_000, direction='B')
        assert len(buy_large_orders) == 2
        assert all(buy_large_orders['direction'] == 'B')
    
    def test_calculate_capital_flow(self):
        """测试资金流向计算"""
        df = pd.DataFrame({
            'code': ['000001'] * 5,
            'time': ['09:35:00', '10:15:00', '13:30:00', '14:15:00', '14:55:00'],
            'price': [10.00] * 5,
            'volume': [100, 200, 300, 400, 500],
            'amount': [100_000, 200_000, 800_000, 400_000, 500_000],
            'direction': ['B', 'B', 'S', 'B', 'S'],
        })
        
        # 计算资金流向
        flow = TickAnalyzer.calculate_capital_flow(df, code='000001', date='2025-12-07')
        
        # 验证
        assert isinstance(flow, CapitalFlowResult)
        assert flow.code == '000001'
        assert flow.date == '2025-12-07'
        assert flow.total_buy_amount == 700_000  # 100k + 200k + 400k
        assert flow.total_sell_amount == 1_300_000  # 800k + 500k
        assert flow.net_inflow == -600_000  # 净流出
        assert not flow.is_inflow
        assert flow.large_order_count == 2  # 800k和500k两笔
        
        # 验证分时段分析
        assert flow.time_analysis is not None
        assert 'morning_open' in flow.time_analysis
        assert 'afternoon' in flow.time_analysis


@pytest.mark.asyncio
class TestTickService:
    """测试 TickService 服务"""
    
    async def test_initialization(self):
        """测试服务初始化"""
        service = TickService()
        
        success = await service.initialize()
        assert success is True
        
        await service.close()
    
    async def test_get_tick_with_mock_data(self, monkeypatch):
        """测试获取分笔数据（使用模拟数据）
        
        注意: 此测试需要连接到真实数据源，标记为集成测试
        """
        pytest.skip("需要真实数据源，移至集成测试")
    
    async def test_get_tick_summary(self, monkeypatch):
        """测试获取统计摘要
        
        注意: 此测试需要连接到真实数据源，标记为集成测试
        """
        pytest.skip("需要真实数据源，移至集成测试")
    
    async def test_analyze_capital_flow(self, monkeypatch):
        """测试资金流向分析
        
        注意: 此测试需要连接到真实数据源，标记为集成测试
        """
        pytest.skip("需要真实数据源，移至集成测试")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

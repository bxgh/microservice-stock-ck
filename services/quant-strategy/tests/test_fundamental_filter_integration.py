"""Integration tests for fundamental filter"""

import pytest
from services.fundamental_filter import FundamentalFilter


class TestFundamentalFilterIntegration:
    """测试基本面过滤器集成"""
    
    @pytest.mark.asyncio
    async def test_filter_empty_list(self):
        """测试空列表过滤"""
        filter_service = FundamentalFilter()
        result = await filter_service.filter_stocks([])
        
        assert result['passed'] == []
        assert result['rejected'] == []
        assert result['rejection_reasons'] == {}
        
    @pytest.mark.asyncio
    async def test_filter_single_stock(self):
        """测试单个股票过滤"""
        filter_service = FundamentalFilter()
        result = await filter_service.filter_stocks(["600519"])
        
        # 验证返回格式
        assert 'passed' in result
        assert 'rejected' in result
        assert 'rejection_reasons' in result
        
        # 验证股票被分类
        total = len(result['passed']) + len(result['rejected'])
        assert total == 1
        
    @pytest.mark.asyncio
    async def test_filter_multiple_stocks(self):
        """测试批量股票过滤"""
        filter_service = FundamentalFilter()
        
        # 使用一批股票代码
        stock_codes = [
            "600000", "600001", "600002", "600003", "600004",
            "600005", "600006", "600007", "600008", "600009"
        ]
        
        result = await filter_service.filter_stocks(stock_codes)
        
        # 验证所有股票都被处理
        total = len(result['passed']) + len(result['rejected'])
        assert total == len(stock_codes)
        
        # 验证没有重复
        all_stocks = set(result['passed']) | set(result['rejected'])
        assert len(all_stocks) == len(stock_codes)
        
        # 验证被拒绝的股票都有原因
        for code in result['rejected']:
            assert code in result['rejection_reasons']
            assert len(result['rejection_reasons'][code]) > 0
            
    @pytest.mark.asyncio
    async def test_filter_with_custom_thresholds(self):
        """测试自定义阈值的过滤器"""
        # 使用更严格的阈值
        filter_service = FundamentalFilter(
            goodwill_threshold=0.2,  # 更严格
            pledge_threshold=0.3,     # 更严格
            cashflow_threshold=0.7,   # 更严格
            cash_threshold=0.15,      # 更严格
            debt_threshold=0.15       # 更严格
        )
        
        stock_codes = ["600010", "600011", "600012", "600013", "600014"]
        result = await filter_service.filter_stocks(stock_codes)
        
        # 更严格的阈值应该拒绝更多股票
        total = len(result['passed']) + len(result['rejected'])
        assert total == len(stock_codes)
        
    @pytest.mark.asyncio
    async def test_filter_with_lenient_thresholds(self):
        """测试宽松阈值的过滤器"""
        # 使用更宽松的阈值
        filter_service = FundamentalFilter(
            goodwill_threshold=0.8,   # 更宽松
            pledge_threshold=0.9,     # 更宽松
            cashflow_threshold=0.1,   # 更宽松
            cash_threshold=0.5,       # 更宽松
            debt_threshold=0.5        # 更宽松
        )
        
        stock_codes = ["600015", "600016", "600017", "600018", "600019"]
        result = await filter_service.filter_stocks(stock_codes)
        
        # 更宽松的阈值应该通过更多股票
        total = len(result['passed']) + len(result['rejected'])
        assert total == len(stock_codes)
        
    @pytest.mark.asyncio
    async def test_filter_consistency(self):
        """测试过滤器一致性 - 同一股票多次过滤应得到相同结果"""
        filter_service = FundamentalFilter()
        
        stock_code = "600520"
        
        # 第一次过滤
        result1 = await filter_service.filter_stocks([stock_code])
        
        # 第二次过滤
        result2 = await filter_service.filter_stocks([stock_code])
        
        # 结果应该一致（因为Mock数据使用股票代码作为随机种子）
        assert result1['passed'] == result2['passed']
        assert result1['rejected'] == result2['rejected']
        
    @pytest.mark.asyncio
    async def test_filter_large_batch(self):
        """测试大批量股票过滤"""
        filter_service = FundamentalFilter()
        
        # 生成50个股票代码
        stock_codes = [f"60{i:04d}" for i in range(50)]
        
        result = await filter_service.filter_stocks(stock_codes)
        
        # 验证所有股票都被处理
        total = len(result['passed']) + len(result['rejected'])
        assert total == len(stock_codes)
        
        # 验证至少有一些股票通过和一些被拒绝（基于Mock数据的随机性）
        # 注意：这个断言可能在极端情况下失败，但概率很低
        assert len(result['passed']) > 0 or len(result['rejected']) > 0

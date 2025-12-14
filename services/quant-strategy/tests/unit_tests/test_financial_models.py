"""Unit tests for financial models"""

import pytest
from models.financial_models import FinancialIndicators


class TestFinancialIndicators:
    """测试财务指标模型"""
    
    def test_model_creation(self):
        """测试模型创建"""
        indicators = FinancialIndicators(
            stock_code="600519",
            report_date="2024-09-30",
            goodwill=5.0,
            net_assets=150.0,
            monetary_funds=30.0,
            total_assets=300.0,
            interest_bearing_debt=20.0,
            operating_cash_flow=15.0,
            net_profit=12.0,
            major_shareholder_pledge_ratio=0.15
        )
        
        assert indicators.stock_code == "600519"
        assert indicators.goodwill == 5.0
        assert indicators.net_assets == 150.0
        
    def test_goodwill_ratio(self):
        """测试商誉比例计算"""
        indicators = FinancialIndicators(
            stock_code="600519",
            report_date="2024-09-30",
            goodwill=30.0,
            net_assets=100.0,
            monetary_funds=10.0,
            total_assets=200.0,
            interest_bearing_debt=20.0,
            operating_cash_flow=10.0,
            net_profit=10.0,
            major_shareholder_pledge_ratio=0.1
        )
        
        assert indicators.goodwill_ratio == 0.3
        
    def test_goodwill_ratio_zero_net_assets(self):
        """测试净资产为零时的商誉比例"""
        indicators = FinancialIndicators(
            stock_code="600519",
            report_date="2024-09-30",
            goodwill=30.0,
            net_assets=0.0,
            monetary_funds=10.0,
            total_assets=200.0,
            interest_bearing_debt=20.0,
            operating_cash_flow=10.0,
            net_profit=10.0,
            major_shareholder_pledge_ratio=0.1
        )
        
        assert indicators.goodwill_ratio == 0.0
        
    def test_cash_to_profit_ratio(self):
        """测试收现比计算"""
        indicators = FinancialIndicators(
            stock_code="600519",
            report_date="2024-09-30",
            goodwill=5.0,
            net_assets=100.0,
            monetary_funds=10.0,
            total_assets=200.0,
            interest_bearing_debt=20.0,
            operating_cash_flow=8.0,
            net_profit=10.0,
            major_shareholder_pledge_ratio=0.1
        )
        
        assert indicators.cash_to_profit_ratio == 0.8
        
    def test_cash_to_profit_ratio_negative_profit(self):
        """测试净利润为负时的收现比"""
        indicators = FinancialIndicators(
            stock_code="600519",
            report_date="2024-09-30",
            goodwill=5.0,
            net_assets=100.0,
            monetary_funds=10.0,
            total_assets=200.0,
            interest_bearing_debt=20.0,
            operating_cash_flow=8.0,
            net_profit=-5.0,
            major_shareholder_pledge_ratio=0.1
        )
        
        assert indicators.cash_to_profit_ratio == 0.0
        
    def test_cash_ratio(self):
        """测试货币资金比例计算"""
        indicators = FinancialIndicators(
            stock_code="600519",
            report_date="2024-09-30",
            goodwill=5.0,
            net_assets=100.0,
            monetary_funds=50.0,
            total_assets=200.0,
            interest_bearing_debt=20.0,
            operating_cash_flow=10.0,
            net_profit=10.0,
            major_shareholder_pledge_ratio=0.1
        )
        
        assert indicators.cash_ratio == 0.25
        
    def test_debt_ratio(self):
        """测试有息负债比例计算"""
        indicators = FinancialIndicators(
            stock_code="600519",
            report_date="2024-09-30",
            goodwill=5.0,
            net_assets=100.0,
            monetary_funds=10.0,
            total_assets=200.0,
            interest_bearing_debt=40.0,
            operating_cash_flow=10.0,
            net_profit=10.0,
            major_shareholder_pledge_ratio=0.1
        )
        
        assert indicators.debt_ratio == 0.2
        
    def test_dual_high_pattern(self):
        """测试存贷双高模式识别"""
        indicators = FinancialIndicators(
            stock_code="600519",
            report_date="2024-09-30",
            goodwill=5.0,
            net_assets=100.0,
            monetary_funds=50.0,  # 25% of total assets
            total_assets=200.0,
            interest_bearing_debt=50.0,  # 25% of total assets
            operating_cash_flow=10.0,
            net_profit=10.0,
            major_shareholder_pledge_ratio=0.1
        )
        
        # Both ratios > 20%, indicating dual-high pattern
        assert indicators.cash_ratio > 0.2
        assert indicators.debt_ratio > 0.2

import pytest
from domain.alpha.risk_factors import (
    StatusRule, LiquidityRule, GoodwillRule, PledgeRule, 
    CashflowQualityRule, FraudRiskRule
)

class TestStatusRule:
    def test_status_checks(self):
        rule = StatusRule()
        
        # Pass case
        assert rule.check({'listing_status': 'L', 'is_st': False, 'is_suspended': False}).passed
        
        # Fail cases
        assert not rule.check({'listing_status': 'D'}).passed
        assert not rule.check({'is_st': True}).passed
        assert not rule.check({'is_suspended': True}).passed

class TestLiquidityRule:
    def test_liquidity_thresholds(self):
        # Min Cap 30B, Min Vol 20M
        rule = LiquidityRule(30.0, 20.0)
        
        # Pass
        assert rule.check({'market_cap': 35.0, 'turnover': 25000000.0}).passed
        
        # Fail Cap
        assert not rule.check({'market_cap': 10.0, 'turnover': 25000000.0}).passed
        
        # Fail Vol
        assert not rule.check({'market_cap': 35.0, 'turnover': 5000000.0}).passed

class TestGoodwillRule:
    def test_goodwill_ratio(self):
        rule = GoodwillRule(0.3) # Max 30%
        
        # Pass (10/100 = 10%)
        assert rule.check({'goodwill': 10, 'net_assets': 100}).passed
        
        # Fail (40/100 = 40%)
        assert not rule.check({'goodwill': 40, 'net_assets': 100}).passed
        
        # Edge case: Negative Equity
        assert not rule.check({'goodwill': 10, 'net_assets': -10}).passed

class TestPledgeRule:
    def test_pledge_ratio(self):
        rule = PledgeRule(0.5)
        
        # Pass
        assert rule.check({'major_shareholder_pledge_ratio': 0.1}).passed
        
        # Fail
        assert not rule.check({'major_shareholder_pledge_ratio': 0.6}).passed

class TestCashflowQualityRule:
    def test_ocf_quality(self):
        rule = CashflowQualityRule(0.5) # Min 0.5 ratio
        
        # Pass (Profit 100, OCF 80 -> 0.8)
        assert rule.check({'net_profit': 100, 'operating_cash_flow': 80}).passed
        
        # Fail (Profit 100, OCF 20 -> 0.2)
        assert not rule.check({'net_profit': 100, 'operating_cash_flow': 20}).passed
        
        # Pass (Loss making - rule skips check)
        assert rule.check({'net_profit': -50, 'operating_cash_flow': -100}).passed

class TestFraudRiskRule:
    def test_high_cash_high_debt(self):
        rule = FraudRiskRule()
        
        # Pass: Normal structure (Low cash, Low debt)
        assert rule.check({
            'total_assets': 1000, 
            'monetary_funds': 100, 
            'interest_bearing_debt': 100
        }).passed
        
        # Fail: Suspicious (Cash 30%, Debt 30%)
        assert not rule.check({
            'total_assets': 1000, 
            'monetary_funds': 300, 
            'interest_bearing_debt': 300
        }).passed

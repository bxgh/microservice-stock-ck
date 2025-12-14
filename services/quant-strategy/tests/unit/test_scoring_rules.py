import pytest
from services.alpha.fundamental_scoring_service import FundamentalScoringService
from domain.models.financial_models import FinancialIndicators
from domain.alpha.scoring_models import ScoringMode


class TestAbsoluteScoringLogic:
    """Test Absolute scoring thresholds"""

    def setup_method(self):
        self.service = FundamentalScoringService()

    def test_roe_scoring_levels(self):
        # Excellent (>15%)
        assert self.service._absolute_roe_score(0.20) == 100.0
        # Good (10-15%)
        assert self.service._absolute_roe_score(0.12) == 80.0
        # Acceptable (5-10%)
        assert self.service._absolute_roe_score(0.07) == 60.0
        # Poor (<5%)
        assert self.service._absolute_roe_score(0.03) == 40.0

    def test_growth_scoring_levels(self):
        # Excellent (>20%)
        assert self.service._absolute_growth_score(0.25) == 100.0
        # Good (10-20%)
        assert self.service._absolute_growth_score(0.15) == 80.0
        # Acceptable (5-10%)
        assert self.service._absolute_growth_score(0.07) == 60.0
        # Marginal (0-5%)
        assert self.service._absolute_growth_score(0.02) == 40.0
        # Negative
        assert self.service._absolute_growth_score(-0.05) == 20.0

    def test_quality_scoring_levels(self):
        # Excellent (OCF/Profit > 1.0)
        assert self.service._absolute_quality_score(1.2) == 100.0
        # Good (0.8-1.0)
        assert self.service._absolute_quality_score(0.9) == 80.0
        # Acceptable (0.5-0.8)
        assert self.service._absolute_quality_score(0.6) == 60.0
        # Poor (<0.5)
        assert self.service._absolute_quality_score(0.3) == 40.0


class TestRelativeScoringLogic:
    """Test Relative (percentile-based) scoring"""

    def setup_method(self):
        self.service = FundamentalScoringService()
        self.mock_distribution = {
            'mean': 0.10,
            'median': 0.10,
            'p25': 0.05,
            'p50': 0.10,
            'p75': 0.15,
            'min': 0.0,
            'max': 0.30
        }

    def test_percentile_score_top(self):
        # Value >= P75 => 100
        assert self.service._percentile_score(0.20, self.mock_distribution) == 100.0

    def test_percentile_score_above_median(self):
        # P50 <= Value < P75 => 80
        assert self.service._percentile_score(0.12, self.mock_distribution) == 80.0

    def test_percentile_score_mid(self):
        # P25 <= Value < P50 => 60
        assert self.service._percentile_score(0.07, self.mock_distribution) == 60.0

    def test_percentile_score_bottom(self):
        # Value < P25 => 40
        assert self.service._percentile_score(0.03, self.mock_distribution) == 40.0


class TestDimensionScoring:
    """Test complete dimension scoring"""

    def setup_method(self):
        self.service = FundamentalScoringService()

    def test_profitability_absolute_mode(self):
        fin = FinancialIndicators(stock_code="TEST", roe=0.12)
        dim_score = self.service._score_profitability(fin, None, ScoringMode.ABSOLUTE)
        
        assert dim_score.dimension_name == "Profitability"
        assert dim_score.mode == ScoringMode.ABSOLUTE
        assert dim_score.weighted_score == 80.0  # ROE 12% => Good

    def test_growth_absolute_mode(self):
        fin = FinancialIndicators(
            stock_code="TEST",
            revenue_growth_yoy=0.15,
            net_profit_growth_yoy=0.25
        )
        dim_score = self.service._score_growth(fin, None, ScoringMode.ABSOLUTE)
        
        avg_growth = (0.15 + 0.25) / 2  # 20%
        assert dim_score.mode == ScoringMode.ABSOLUTE
        assert dim_score.weighted_score == 100.0  # 20% => Excellent

    def test_quality_scoring(self):
        fin = FinancialIndicators(
            stock_code="TEST",
            operating_cash_flow=90.0,
            net_profit=100.0
        )
        dim_score = self.service._score_quality(fin, None, ScoringMode.ABSOLUTE)
        
        assert dim_score.mode == ScoringMode.ABSOLUTE
        assert dim_score.weighted_score == 80.0  # 0.9 ratio => Good

"""
Fundamental Scoring Service - EPIC-002 Story 2.2
Implements Hybrid Scoring: Relative (industry-based) with Absolute fallback.
"""
import logging

from config.settings import settings
from domain.alpha.scoring_models import DimensionScore, FundamentalScore, ScoreDetail, ScoringMode
from domain.models.financial_models import FinancialIndicators

logger = logging.getLogger(__name__)


class FundamentalScoringService:
    """
    Core service for fundamental stock scoring.
    Supports both Relative (industry percentile) and Absolute (fixed threshold) modes.
    """

    async def initialize(self):
        """Async initialization"""
        pass

    async def close(self):
        """Cleanup resources"""
        pass

    def __init__(self, data_provider=None):
        self.data_provider = data_provider
        self.weights = {
            'profitability': settings.weight_profitability,
            'growth': settings.weight_growth,
            'quality': settings.weight_quality
        }

    async def score_stock(
        self,
        code: str,
        financials: FinancialIndicators | None = None,
        industry_stats: dict | None = None,
        mode: ScoringMode = ScoringMode.ABSOLUTE
    ) -> FundamentalScore | None:
        """
        Calculate fundamental score for a stock.

        Args:
            code: Stock code
            financials: Pre-fetched financial data (optional, fetches if None)
            industry_stats: Pre-fetched industry stats (optional)
            mode: Scoring mode (RELATIVE/ABSOLUTE) - acts as hint/override

        Returns:
            FundamentalScore or None if data unavailable
        """
        # 1. Fetch Financial Data if not provided
        if not financials:
            if not self.data_provider:
                from adapters.stock_data_provider import data_provider as default_dp
                self.data_provider = default_dp

            financials = await self.data_provider.get_financial_indicators(code)

        if not financials:
            logger.warning(f"No financial data for {code}")
            return None

        # 2. Determine Mode and Fetch Industry Stats if needed
        # If financials provided but no industry_stats, we can try to fetch if we have industry info?
        # But here we assume caller handles data fetching for optimization.
        # If mode is RELATIVE and stats missing, downgrade to ABSOLUTE

        final_mode = mode
        if mode == ScoringMode.RELATIVE and not industry_stats:
            # Try to fetch if provider available?
            # Ideally caller provides it. Verify logic.
             logger.debug(f"Relative mode requested but no industry stats for {code}, fallback to Absolute")
             final_mode = ScoringMode.ABSOLUTE
        elif industry_stats:
             final_mode = ScoringMode.RELATIVE

        mode = final_mode

        # 3. Use determined mode (logic moved up)

        # Retrieve History ROE Std (Mock or placeholder for MOAT penalty)
        history_roe_std = 0.05 # placeholder for stability

        # 4. Calculate Dimension Scores
        profitability = self._score_profitability(financials, industry_stats, mode, history_roe_std)
        growth = self._score_growth(financials, industry_stats, mode)
        quality = self._score_quality(financials, industry_stats, mode)

        # 5. Calculate Total
        total = (
            profitability.weighted_score * self.weights['profitability'] +
            growth.weighted_score * self.weights['growth'] +
            quality.weighted_score * self.weights['quality']
        )

        return FundamentalScore(
            stock_code=code,
            total_score=total,
            profitability=profitability,
            growth=growth,
            quality=quality,
            scoring_mode=mode,
            industry_code=None # Caller knows industry
        )

    def _score_profitability(
        self,
        fin: FinancialIndicators,
        industry_stats: dict | None,
        mode: ScoringMode,
        history_roe_std: float | None = None
    ) -> DimensionScore:
        """Score profitability dimension (ROE focus with stability penalty)"""
        roe = fin.roe if fin.roe is not None else 0.0

        if mode == ScoringMode.RELATIVE and industry_stats and 'roe_stats' in industry_stats:
            roe_dist = industry_stats['roe_stats']
            raw_score = self._percentile_score(roe, roe_dist)
            percentile = self._calculate_percentile(roe, roe_dist)
        else:
            raw_score = self._absolute_roe_score(roe)
            percentile = None

        # ROE Stability Penalty (Moat)
        penalty = 0.0
        if history_roe_std is not None:
            if history_roe_std > 0.15: # Highly unstable ROE (>15% std)
                penalty = 30.0
            elif history_roe_std > 0.08:
                penalty = 15.0

            raw_score = max(0.0, raw_score - penalty)

        detail = ScoreDetail(
            metric_name="ROE",
            value=roe,
            raw_score=raw_score,
            weight=1.0,
            percentile=percentile,
            threshold=settings.roe_good if mode == ScoringMode.ABSOLUTE else None
        )

        return DimensionScore(
            dimension_name="Profitability",
            weighted_score=raw_score,
            metrics=[detail],
            mode=mode
        )

    def _score_growth(
        self,
        fin: FinancialIndicators,
        industry_stats: dict | None,
        mode: ScoringMode
    ) -> DimensionScore:
        """Score growth dimension (Revenue & Profit YoY growth)"""
        rev_growth = fin.revenue_growth_yoy if fin.revenue_growth_yoy is not None else 0.0
        profit_growth = fin.net_profit_growth_yoy if fin.net_profit_growth_yoy is not None else 0.0
        avg_growth = (rev_growth + profit_growth) / 2.0

        if mode == ScoringMode.RELATIVE and industry_stats and 'revenue_growth_stats' in industry_stats:
            growth_dist = industry_stats['revenue_growth_stats']
            raw_score = self._percentile_score(avg_growth, growth_dist)
            percentile = self._calculate_percentile(avg_growth, growth_dist)
        else:
            raw_score = self._absolute_growth_score(avg_growth)
            percentile = None

        detail = ScoreDetail(
            metric_name="Growth (Avg YoY)",
            value=avg_growth,
            raw_score=raw_score,
            weight=1.0,
            percentile=percentile
        )

        return DimensionScore(
            dimension_name="Growth",
            weighted_score=raw_score,
            metrics=[detail],
            mode=mode
        )

    def _score_quality(
        self,
        fin: FinancialIndicators,
        industry_stats: dict | None,
        mode: ScoringMode
    ) -> DimensionScore:
        """Score earnings quality (OCF/NetProfit ratio)"""
        ocf = fin.operating_cash_flow if fin.operating_cash_flow is not None else 0.0
        profit = fin.net_profit if fin.net_profit is not None else 1.0

        quality_ratio = 0.0 if profit <= 0 else ocf / profit

        # Use absolute scoring (no industry stats for this metric typically)
        raw_score = self._absolute_quality_score(quality_ratio)

        detail = ScoreDetail(
            metric_name="OCF Quality",
            value=quality_ratio,
            raw_score=raw_score,
            weight=1.0,
            threshold=settings.ocf_quality_good
        )

        return DimensionScore(
            dimension_name="Quality",
            weighted_score=raw_score,
            metrics=[detail],
            mode=ScoringMode.ABSOLUTE  # Quality always absolute
        )

    # --- Relative Scoring Helpers ---

    def _percentile_score(self, value: float, distribution: dict) -> float:
        """
        Score based on percentile within industry distribution.
        distribution should contain: mean, median, p25, p50, p75
        """
        p25 = distribution.get('p25', distribution.get('percentile_25', 0))
        p50 = distribution.get('p50', distribution.get('median', distribution.get('percentile_50', 0)))
        p75 = distribution.get('p75', distribution.get('percentile_75', 0))

        if value >= p75:
            return 100.0
        elif value >= p50:
            return 80.0
        elif value >= p25:
            return 60.0
        else:
            return 40.0

    def _calculate_percentile(self, value: float, distribution: dict) -> float:
        """Estimate percentile position (0-1)"""
        min_val = distribution.get('min', 0)
        max_val = distribution.get('max', 100)

        if max_val == min_val:
            return 0.5

        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

    # --- Absolute Scoring Helpers ---

    def _absolute_roe_score(self, roe: float) -> float:
        """Absolute ROE scoring"""
        if roe >= settings.roe_excellent:
            return 100.0
        elif roe >= settings.roe_good:
            return 80.0
        elif roe >= settings.roe_acceptable:
            return 60.0
        else:
            return 40.0

    def _absolute_growth_score(self, growth: float) -> float:
        """Absolute growth scoring (YoY %)"""
        if growth >= settings.growth_excellent:
            return 100.0
        elif growth >= settings.growth_good:
            return 80.0
        elif growth >= settings.growth_acceptable:
            return 60.0
        elif growth >= 0:
            return 40.0
        else:
            return 20.0  # Negative growth

    def _absolute_quality_score(self, ratio: float) -> float:
        """Absolute quality scoring (OCF/Profit)"""
        if ratio >= settings.ocf_quality_excellent:
            return 100.0
        elif ratio >= settings.ocf_quality_good:
            return 80.0
        elif ratio >= 0.5:
            return 60.0
        else:
            return 40.0


# Global Singleton
fundamental_scoring_service = FundamentalScoringService()

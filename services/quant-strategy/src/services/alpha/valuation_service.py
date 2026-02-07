"""
Valuation Service - EPIC-002 Story 2.3
Implements PE/PB Band Valuation Scoring using real historical data.
"""
import logging
from typing import Any

from config.settings import settings
from domain.alpha.valuation_models import ValuationBandScore, ValuationScore

logger = logging.getLogger(__name__)



class ValuationService:
    """
    Service for calculating valuation scores (PE/PB Band Method).
    """

    async def initialize(self):
        """Async initialization"""
        pass

    async def close(self):
        """Cleanup resources"""
        pass

    def __init__(self, data_provider=None):
        self.data_provider = data_provider

    async def score_stock(
        self,
        code: str,
        current_valuation: dict | None = None
    ) -> ValuationScore | None:
        """
        Calculate valuation score based on historical PE/PB bands.

        Args:
            code: Stock code
            current_valuation: Pre-fetched valuation data (optional)

        Returns:
            ValuationScore object or None if insufficient data
        """
        # 1. Fetch Current Valuation if not provided
        if not current_valuation:
            if not self.data_provider:
                from adapters.stock_data_provider import data_provider as default_dp
                self.data_provider = default_dp

            current_valuation = await self.data_provider.get_valuation(code)

        current_data = current_valuation
        if not current_data:
            logger.warning(f"No current valuation for {code} - skipping valuation score")
            return None

        # 2. Fetch Historical Valuation (for Band Analysis)
        if not self.data_provider:
             from adapters.stock_data_provider import data_provider as default_dp
             self.data_provider = default_dp

        history_data = await self.data_provider.get_valuation_history(code, years=5)
        if not history_data or 'stats' not in history_data:
            logger.warning(f"No valuation history for {code} - skipping valuation score")
            return None

        stats = history_data['stats']

        # 3. Calculate PE Band Score
        current_pe = current_data.get('pe_ttm')
        pe_stats = stats.get('pe_ttm', {})
        pe_score = self._calculate_band_score("PE", current_pe, pe_stats)

        # 4. Calculate PB Band Score
        current_pb = current_data.get('pb_ratio')
        pb_stats = stats.get('pb_ratio', {})
        pb_score = self._calculate_band_score("PB", current_pb, pb_stats)

        # 5. Aggregate
        if pe_score and pb_score:
            total_score = (
                pe_score.band_score * settings.weight_pe_score +
                pb_score.band_score * settings.weight_pb_score
            )
            # Determine Status
            if total_score >= 80:
                status = "Undervalued"
            elif total_score <= 40:
                status = "Overvalued"
            else:
                status = "Fair Value"

            return ValuationScore(
                stock_code=code,
                total_score=total_score,
                pe_score=pe_score,
                pb_score=pb_score,
                valuation_status=status
            )

        return None

    def _calculate_band_score(
        self,
        metric_name: str,
        current_value: float | None,
        stats: dict[str, Any]
    ) -> ValuationBandScore | None:
        """Calculate score for a single metric based on history"""
        if current_value is None or not stats:
            return None

        # Extract stats
        min_val = stats.get('min', 0)
        max_val = stats.get('max', 100)
        median_val = stats.get('median', 50)

        # Validate data integrity
        if max_val <= min_val:
            return None

        # Calculate Percentile (0-100)
        # Formula: (Current - Min) / (Max - Min) * 100
        # Lower percentile = Cheaper = Higher Score
        percentile = (current_value - min_val) / (max_val - min_val) * 100
        percentile = max(0.0, min(100.0, percentile)) # Clamp

        # Map Percentile to Score (Inverted relationship)
        if percentile < settings.val_undervalued_pct:
            # < 25%: Cheap -> 100 pts
            band_score = 100.0
        elif percentile < settings.val_fair_low_pct:
            # 25-50%: Fair/Cheap -> 80 pts
            band_score = 80.0
        elif percentile < settings.val_fair_high_pct:
            # 50-75%: Fair/Expensive -> 60 pts
            band_score = 60.0
        elif percentile < settings.val_overvalued_pct:
            # 75-90%: Expensive -> 40 pts
            band_score = 40.0
        else:
            # > 90%: Bubble -> 20 pts
            band_score = 20.0

        return ValuationBandScore(
            metric_name=metric_name,
            current_value=current_value,
            percentile=percentile,
            band_score=band_score,
            min_value=min_val,
            max_value=max_val,
            median_value=median_val
        )

# Global Singleton
valuation_service = ValuationService()

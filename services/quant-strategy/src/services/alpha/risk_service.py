"""
Risk Veto Service
Orchestrates the risk filtering process for the Alpha Scoring Engine.
"""
import logging

from adapters.stock_data_provider import data_provider
from config.settings import settings
from domain.alpha.risk_factors import (
    CashflowQualityRule,
    FraudRiskRule,
    GoodwillRule,
    LiquidityRule,
    PledgeRule,
    RiskAssessment,
    RiskFactor,
    StatusRule,
)

logger = logging.getLogger(__name__)

class RiskVetoService:
    """
    Main entry point for stock risk filtering.
    """

    def __init__(self):
        # Initialize Rules with thresholds from Settings
        self.rules = [
            StatusRule(),
            LiquidityRule(
                min_market_cap_billion=settings.min_market_cap_billion,
                min_volume_million=settings.min_avg_daily_volume_million
            ),
            GoodwillRule(max_ratio=settings.max_goodwill_ratio),
            PledgeRule(max_ratio=settings.max_pledge_ratio),
            CashflowQualityRule(min_ratio=settings.min_cashflow_quality),
            FraudRiskRule()
        ]

    async def check_stocks(self, stock_codes: list[str]) -> list[RiskAssessment]:
        """
        Batch check a list of stocks against all risk rules.
        """
        results = []
        for code in stock_codes:
            assessment = await self.check_single_stock(code)
            results.append(assessment)
        return results

    async def check_single_stock(self, code: str) -> RiskAssessment:
        """
        Run all risk checks for a single stock.
        """
        # 1. Fetch Data
        # We need: Market Info (Price, Cap, Status) + Financials (Goodwill, Cash, etc.)

        # Parallel fetch could be better, but simple sequential for now.
        market_info = await data_provider.get_stock_info(code) or {}
        financials = await data_provider.get_financial_indicators(code)

        # Merge data into a single dict for rules
        # Financials might be Pydantic model or None
        fin_dict = financials.dict() if financials else {}

        # Construct the composite data context
        data_context = {
            # Market Data
            'listing_status': market_info.get('listing_status', 'L'),
            'is_st': market_info.get('is_st', False),
            'is_suspended': market_info.get('is_suspended', False),
            'market_cap': market_info.get('market_cap', 0.0), # Assuming Billions from API/Provider
            'turnover': market_info.get('amount', 0.0), # Ensure this matches API key. Check Provider later.

            # Financial Data
            **fin_dict
        }

        # 2. Apply Rules
        factors: list[RiskFactor] = []
        veto_reasons: list[str] = []
        is_vetoed = False

        for rule in self.rules:
            result = rule.check(data_context)
            factors.append(result)

            if not result.passed:
                is_vetoed = True
                veto_reasons.append(f"[{rule.name}] {result.reason}")

                # Option: Short-circuit?
                # For detailed reports, maybe not. For speed, yes.
                # Let's assess all for now to give full feedback.

        return RiskAssessment(
            stock_code=code,
            is_vetoed=is_vetoed,
            veto_reasons=veto_reasons,
            details=factors
        )

# Singleton
risk_service = RiskVetoService()

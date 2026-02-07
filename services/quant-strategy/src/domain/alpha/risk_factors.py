"""
Risk Factors Domain Layer - EPIC-002 Story 2.1
Defines core risk assessment models and veto rules.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RiskFactor(BaseModel):
    """Result of a single risk check"""
    rule_name: str
    passed: bool
    reason: str
    value: float
    threshold: float
    timestamp: str = str(datetime.now())

class RiskAssessment(BaseModel):
    """Aggregate result of all risk checks for a stock"""
    stock_code: str
    is_vetoed: bool
    veto_reasons: list[str]
    details: list[RiskFactor]
    assessed_at: str = str(datetime.now())

class RiskRule(ABC):
    """Abstract base class for all risk veto rules"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def check(self, data: dict[str, Any]) -> RiskFactor:
        """
        Evaluate if the stock passes this risk rule.

        Args:
            data: Dictionary containing relevant stock data (financials, market info, etc.)

        Returns:
            RiskFactor object containing the check result
        """
        pass

# --- Concrete Rule Implementations ---

class StatusRule(RiskRule):
    """Filters out ST, suspended, or delisting stocks"""

    def __init__(self):
        super().__init__("Status Check")

    def check(self, data: dict[str, Any]) -> RiskFactor:
        # Check standard flags. If missing, assume Safe (or Dangerous, depending on strictness).
        # Here we assume data provider gives explicit flags.
        is_st = data.get('is_st', False)
        is_suspended = data.get('is_suspended', False)
        status = data.get('listing_status', 'L') # L=Listed, D=Delisted, P=Paused

        passed = not (is_st or is_suspended or status != 'L')

        reasons = []
        if is_st:
            reasons.append("ST Stock")
        if is_suspended:
            reasons.append("Suspended")
        if status != 'L':
            reasons.append(f"Status {status}")

        return RiskFactor(
            rule_name=self.name,
            passed=passed,
            reason=", ".join(reasons) if not passed else "Normal Status",
            value=1.0 if not passed else 0.0,
            threshold=0.0
        )

class LiquidityRule(RiskRule):
    """Filters based on market cap and volume"""

    def __init__(self, min_market_cap_billion: float, min_volume_million: float):
        super().__init__("Liquidity Check")
        self.min_cap = min_market_cap_billion
        self.min_vol = min_volume_million

    def check(self, data: dict[str, Any]) -> RiskFactor:
        market_cap = data.get('market_cap', 0.0) # In Billions
        avg_turnover = data.get('turnover', 0.0) # In Yuan

        # Convert turnover to millions for comparison if needed, or keep consistent units.
        # Assuming DataProvider gives turnover in Yuan, convert to Millions.
        turnover_million = avg_turnover / 1000000.0 if avg_turnover else 0.0

        passed = (market_cap >= self.min_cap) and (turnover_million >= self.min_vol)

        reason = "Pass"
        fail_details = []
        if market_cap < self.min_cap:
            fail_details.append(f"Cap {market_cap:.2f}B < {self.min_cap}B")
        if turnover_million < self.min_vol:
            fail_details.append(f"Vol {turnover_million:.2f}M < {self.min_vol}M")

        if not passed:
            reason = ", ".join(fail_details)

        return RiskFactor(
            rule_name=self.name,
            passed=passed,
            reason=reason,
            value=min(market_cap, turnover_million), # Simplified value representation
            threshold=self.min_cap
        )

class GoodwillRule(RiskRule):
    """Filters stocks with excessive goodwill relative to net assets"""

    def __init__(self, max_ratio: float):
        super().__init__("Goodwill Risk")
        self.max_ratio = max_ratio

    def check(self, data: dict[str, Any]) -> RiskFactor:
        goodwill = data.get('goodwill', 0.0)
        net_assets = data.get('net_assets', 1.0) # Avoid div by zero

        if net_assets <= 0:
             return RiskFactor(
                rule_name=self.name,
                passed=False,
                reason="Negative Net Assets",
                value=net_assets,
                threshold=0.0
            )

        ratio = goodwill / net_assets
        passed = ratio <= self.max_ratio

        return RiskFactor(
            rule_name=self.name,
            passed=passed,
            reason=f"Goodwill/Equity {ratio:.1%} > {self.max_ratio:.0%}" if not passed else f"Ratio {ratio:.1%}",
            value=ratio,
            threshold=self.max_ratio
        )

class PledgeRule(RiskRule):
    """Filters stocks with high major shareholder pledge ratio"""

    def __init__(self, max_ratio: float):
        super().__init__("Pledge Risk")
        self.max_ratio = max_ratio

    def check(self, data: dict[str, Any]) -> RiskFactor:
        ratio = data.get('major_shareholder_pledge_ratio', 0.0)
        # Handle cases where data might be None
        if ratio is None:
            ratio = 0.0

        passed = ratio <= self.max_ratio

        return RiskFactor(
            rule_name=self.name,
            passed=passed,
            reason=f"Pledge Ratio {ratio:.1%} > {self.max_ratio:.0%}" if not passed else f"Ratio {ratio:.1%}",
            value=ratio,
            threshold=self.max_ratio
        )

class CashflowQualityRule(RiskRule):
    """
    Checks Earnings Quality via OCF/NetProfit.
    Only applies if NetProfit is positive. If profitable but poor cashflow -> Fail.
    """

    def __init__(self, min_ratio: float):
        super().__init__("Cashflow Quality")
        self.min_ratio = min_ratio

    def check(self, data: dict[str, Any]) -> RiskFactor:
        net_profit = data.get('net_profit', 0.0)
        ocf = data.get('operating_cash_flow', 0.0)

        if net_profit <= 0:
            # If loss-making, this rule might strictly not apply or we can fail it.
            # Usually for 'Growth', we might ignore loss. For 'Value', loss is bad.
            # Strategy Decision: For Risk Veto, we focus on 'Fake Profit'.
            # If Loss, it fails basic profitability check (which might be another rule),
            # but here we pass it or mark N/A. Let's Pass it here and let 'ProfitabilityRule' handle losses.
            return RiskFactor(
                rule_name=self.name,
                passed=True,
                reason="Loss making (OCF check skipped)",
                value=0.0,
                threshold=self.min_ratio
            )

        ratio = ocf / net_profit
        passed = ratio >= self.min_ratio

        return RiskFactor(
            rule_name=self.name,
            passed=passed,
            reason=f"OCF/Profit {ratio:.2f} < {self.min_ratio}" if not passed else f"Quality {ratio:.2f}",
            value=ratio,
            threshold=self.min_ratio
        )

class FraudRiskRule(RiskRule):
    """
    '存贷双高' Check: High Cash + High Debt.
    Logic: (Cash/Assets > 20%) AND (Debt/Assets > 20%)
    """

    def __init__(self):
        super().__init__("Fraud Risk (存贷双高)")

    def check(self, data: dict[str, Any]) -> RiskFactor:
        cash = data.get('monetary_funds', 0.0)
        debt = data.get('interest_bearing_debt', 0.0)
        assets = data.get('total_assets', 1.0)

        if assets <= 0:
            return RiskFactor(self.name, False, "Invalid Assets", 0.0, 0.0)

        cash_ratio = cash / assets
        debt_ratio = debt / assets

        is_suspicious = (cash_ratio > 0.20) and (debt_ratio > 0.20)

        return RiskFactor(
            rule_name=self.name,
            passed=not is_suspicious,
            reason=f"High Cash ({cash_ratio:.0%}) & High Debt ({debt_ratio:.0%})" if is_suspicious else "Normal Structure",
            value=max(cash_ratio, debt_ratio),
            threshold=0.20
        )

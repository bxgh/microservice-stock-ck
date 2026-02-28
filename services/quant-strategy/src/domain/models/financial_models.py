
from pydantic import BaseModel


class FinancialIndicators(BaseModel):
    """
    Core Financial Indicators for Stock Analysis (EPIC-002)
    Includes data points required for both Risk Veto (Story 2.1) and Scoring (Story 2.2).
    """
    stock_code: str
    report_date: str | None = None

    # --- Balance Sheet Core ---
    total_assets: float | None = None
    net_assets: float | None = None
    goodwill: float | None = None              # For Goodwill Risk
    monetary_funds: float | None = None        # For Fraud Check
    interest_bearing_debt: float | None = None # For Fraud Check

    # --- Income Statement Core ---
    revenue: float | None = None
    net_profit: float | None = None

    # --- Cash Flow Core ---
    operating_cash_flow: float | None = None   # For Quality Check

    # --- Other Indicators ---
    major_shareholder_pledge_ratio: float | None = None # For Pledge Risk

    # --- Ratios (Pre-calculated or derived) ---
    roe: float | None = None
    gross_margin: float | None = None
    revenue_growth_yoy: float | None = None
    net_profit_growth_yoy: float | None = None
    dividend_yield: float | None = None

    @property
    def goodwill_ratio(self) -> float:
        """商誉占净资产比例"""
        if self.goodwill is None or self.net_assets is None or self.net_assets <= 0:
            return 0.0
        return self.goodwill / self.net_assets

    @property
    def cash_to_profit_ratio(self) -> float:
        """收现比: 经营现金流 / 净利润"""
        if self.operating_cash_flow is None or self.net_profit is None or self.net_profit <= 0:
            return 0.0
        return self.operating_cash_flow / self.net_profit

    @property
    def cash_ratio(self) -> float:
        """货币资金占总资产比例"""
        if self.monetary_funds is None or self.total_assets is None or self.total_assets <= 0:
            return 0.0
        return self.monetary_funds / self.total_assets

    @property
    def debt_ratio(self) -> float:
        """有息负债占总资产比例"""
        if self.interest_bearing_debt is None or self.total_assets is None or self.total_assets <= 0:
            return 0.0
        return self.interest_bearing_debt / self.total_assets


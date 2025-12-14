
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

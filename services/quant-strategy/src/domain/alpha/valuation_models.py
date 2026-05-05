"""
Valuation Analysis Domain Models - EPIC-002 Story 2.3
Defines models for PE/PB Band valuation scoring.
"""
from datetime import datetime

from pydantic import BaseModel


class ValuationBandScore(BaseModel):
    """Score detail for a specific valuation metric (PE or PB)"""
    metric_name: str  # "PE" or "PB"
    current_value: float
    percentile: float  # 0-100 position in history
    band_score: float  # 0-100 score (Low percentile = High score)
    min_value: float
    max_value: float
    median_value: float


class ValuationScore(BaseModel):
    """Complete valuation score for a stock"""
    stock_code: str
    total_score: float  # Weighted average of PE and PB scores
    pe_score: ValuationBandScore
    pb_score: ValuationBandScore
    peg_score: float | None = None
    dividend_score: float | None = None
    valuation_status: str  # Undervalued/Fair/Overvalued
    scored_at: str = str(datetime.now())

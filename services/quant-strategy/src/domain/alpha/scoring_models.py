"""
Fundamental Scoring Domain Models - EPIC-002 Story 2.2
Defines scoring models supporting both Relative and Absolute scoring modes.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ScoringMode(str, Enum):
    """Scoring methodology"""
    RELATIVE = "relative"  # Industry-relative scoring
    ABSOLUTE = "absolute"  # Fixed threshold scoring


class ScoreDetail(BaseModel):
    """Individual metric score detail"""
    metric_name: str
    value: float | None
    raw_score: float  # 0-100
    weight: float  # Dimension weight
    percentile: float | None = None  # Industry percentile (0-1) if RELATIVE mode
    threshold: float | None = None  # Threshold used if ABSOLUTE mode


class DimensionScore(BaseModel):
    """Aggregate score for a dimension (Profitability/Growth/Quality)"""
    dimension_name: str
    weighted_score: float  # 0-100
    metrics: list[ScoreDetail]
    mode: ScoringMode


class FundamentalScore(BaseModel):
    """Complete fundamental score for a stock"""
    stock_code: str
    total_score: float  # 0-100 weighted total
    profitability: DimensionScore
    growth: DimensionScore
    quality: DimensionScore
    scoring_mode: ScoringMode
    industry_code: str | None = None
    scored_at: str = str(datetime.now())

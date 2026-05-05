from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
import datetime

# Mock the schema from schemas.py
class IndustryStatsResponse(BaseModel):
    """Industry Statistics Response"""
    industry_code: str
    industry_name: str
    stock_count: int
    report_date: str
    
    # Valuation Distribution
    pe_ttm_stats: Dict[str, float] = Field(..., description="PE TTM 统计 (mean, median, p25/50/75)")
    pb_ratio_stats: Dict[str, float] = Field(..., description="PB 统计")
    
    # Performance Distribution
    roe_stats: Optional[Dict[str, float]] = Field(None, description="ROE 统计")
    revenue_growth_stats: Optional[Dict[str, float]] = Field(None, description="营收增长率统计")

# Mock the service response
# Notice 'count' is int
service_result = {
    'industry_code': '', 
    'industry_name': 'Test Industry',
    'stock_count': 38,
    'report_date': '2024-05-20',
    'pe_ttm_stats': {
        'mean': 28.5,
        'median': 24.1,
        'p25': 18.2,
        'p75': 35.6,
        'count': 38  # Integer!
    },
    'pb_ratio_stats': {
        'mean': 4.2,
        'median': 3.5,
        'count': 38 # Integer!
    },
    'roe_stats': {},
    'revenue_growth_stats': {} 
}

try:
    model = IndustryStatsResponse(**service_result)
    print("✅ Validation Successful")
    print(model.model_dump())
except Exception as e:
    print("❌ Validation Failed")
    print(e)

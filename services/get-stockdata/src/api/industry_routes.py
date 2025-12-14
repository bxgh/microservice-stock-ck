# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request, Query
from typing import Dict, Any, Optional

from data_services.schemas import IndustryStatsResponse
from data_services.industry_service import IndustryService

router = APIRouter(prefix="/api/v1/finance/industry", tags=["行业数据"])

def get_industry_service(request: Request) -> IndustryService:
    """Dependency to get IndustryService from app state"""
    service = getattr(request.app.state, "industry_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="Industry Service not initialized")
    return service

@router.get("/{industry_code}/stats", response_model=IndustryStatsResponse)
async def get_industry_stats(
    industry_code: str,
    request: Request
):
    """
    获取行业统计数据 (PE/PB等估值分布)
    
    Args:
        industry_code: 行业名称 (如 "酿酒行业") 或 代码
    """
    service = get_industry_service(request)
    
    # Assuming industry_code matches name for now or service handles it
    data = await service.get_industry_stats(industry_code)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No stats found for industry: {industry_code}")
        
    return data

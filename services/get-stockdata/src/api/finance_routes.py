# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request, Query
from typing import Dict, Any, Optional

from data_services.schemas import FinancialIndicatorsResponse, FinancialHistoryResponse, IndustryStatsResponse
from data_services.financial_service import FinancialService
from data_services.industry_service import IndustryService
from urllib.parse import unquote

router = APIRouter(prefix="/api/v1/finance", tags=["财务数据"])

def get_financial_service(request: Request) -> FinancialService:
    """Dependency to get FinancialService from app state"""
    service = getattr(request.app.state, "financial_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="Financial Service not initialized")
    return service

def get_industry_service(request: Request) -> IndustryService:
    """Dependency to get IndustryService from app state"""
    service = getattr(request.app.state, "industry_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="Industry Service not initialized")
    return service

@router.get("/indicators/{stock_code}", response_model=FinancialIndicatorsResponse)
async def get_enhanced_indicators(
    stock_code: str,
    request: Request
):
    """
    获取增强财务指标 (EPIC-002)
    包含: 营收、利润、资产、负债、现金流等关键指标
    """
    service = get_financial_service(request)
    data = await service.get_enhanced_indicators(stock_code)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No financial data found for {stock_code}")
        
    return data

@router.get("/history/{stock_code}", response_model=FinancialHistoryResponse)
async def get_financial_history(
    stock_code: str,
    periods: int = Query(8, ge=1, le=20, description="历史期数"),
    report_type: str = Query("Q", description="报告类型 (Q=季报, A=年报)"),
    request: Request = None
):
    """
    获取历史财务数据
    """
    service = get_financial_service(request)
    data = await service.get_financial_history(stock_code, periods=periods, report_type=report_type)
    
    if not data or not data.get("data"):
        raise HTTPException(status_code=404, detail=f"No financial history found for {stock_code}")
        
    return data

@router.get("/industry/{industry_code}/stats", response_model=IndustryStatsResponse)
async def get_industry_stats(
    industry_code: str,
    request: Request
):
    """
    获取行业统计数据
    industry_code 可以是行业代码或URL编码的行业名称
    """
    service = get_industry_service(request)
    
    # Try to decode if it looks encoded (simple check: industry_code usually alphanumeric)
    # Actually industry_service expects name. 
    # The verification script sends encoded name.
    try:
        industry_name = unquote(industry_code)
    except:
        industry_name = industry_code
        
    data = await service.get_industry_stats(industry_name)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No stats found for industry {industry_name}")
        
    return data

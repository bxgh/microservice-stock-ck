# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request, Query
from typing import Dict, Any, Optional

from data_services.schemas import ValuationResponse, ValuationHistoryResponse
from data_services.valuation_service import ValuationService

router = APIRouter(prefix="/api/v1/market/valuation", tags=["市场估值"])

def get_valuation_service(request: Request) -> ValuationService:
    """Dependency to get ValuationService from app state"""
    service = getattr(request.app.state, "valuation_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="Valuation Service not initialized")
    return service

@router.get("/{stock_code}", response_model=ValuationResponse)
async def get_current_valuation(
    stock_code: str,
    request: Request
):
    """
    获取实时估值指标 (PE/PB/市值)
    """
    service = get_valuation_service(request)
    data = await service.get_current_valuation(stock_code)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No valuation data found for {stock_code}")
        
    return data

@router.get("/{stock_code}/history", response_model=ValuationHistoryResponse)
async def get_valuation_history(
    stock_code: str,
    years: int = Query(5, ge=1, le=10, description="历史年数"),
    frequency: str = Query("D", regex="^(D|W|M)$", description="频率 (D=日, W=周, M=月)"),
    request: Request = None
):
    """
    获取历史估值走势与统计
    """
    service = get_valuation_service(request)
    data = await service.get_valuation_history(stock_code, years=years, frequency=frequency)
    
    if not data or not data.get("stats"):
        raise HTTPException(status_code=404, detail=f"No valuation history found for {stock_code}")
        
    return data

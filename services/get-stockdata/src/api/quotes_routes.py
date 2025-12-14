# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from data_services.quotes_service import QuotesService

router = APIRouter(prefix="/api/v1/quotes", tags=["实时行情"])

class RealtimeQuoteResponse(BaseModel):
    code: str
    name: str
    price: Optional[float]
    change_pct: Optional[float]
    volume: Optional[int]
    turnover: Optional[float]
    turnover_ratio: Optional[float]
    market_cap: Optional[float]
    timestamp: str

class BatchQuotesResponse(BaseModel):
    success: bool
    data: List[RealtimeQuoteResponse]
    count: int

def get_quotes_service(request: Request) -> QuotesService:
    service = getattr(request.app.state, "quotes_service", None)
    if not service:
        # Check if initialized but not in state (dev fallback)
        raise HTTPException(status_code=503, detail="Quotes Service not initialized")
    return service

@router.get("/realtime", response_model=BatchQuotesResponse)
async def get_realtime_quotes(
    codes: str = Query(..., description="股票代码列表，逗号分隔 (e.g. 600519,000001)"),
    request: Request = None
):
    """
    批量获取实时行情
    """
    service = get_quotes_service(request)
    
    # Parse codes
    code_list = [c.strip() for c in codes.split(',') if c.strip()]
    if not code_list:
        return BatchQuotesResponse(success=True, data=[], count=0)
        
    quotes = await service.get_realtime_quotes(code_list)
    
    return BatchQuotesResponse(
        success=True,
        data=quotes,
        count=len(quotes)
    )

# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request, Path
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from data_services.liquidity_service import LiquidityService

router = APIRouter(prefix="/api/v1/stocks", tags=["流动性数据"])

class OrderBookLevel(BaseModel):
    price: float
    volume: int

class OrderBook(BaseModel):
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: str
    simulated: bool = False

class LiquidityResponse(BaseModel):
    success: bool
    data: Dict[str, Any] # Flexible dict for now to match flexible service return

def get_liquidity_service(request: Request) -> LiquidityService:
    service = getattr(request.app.state, "liquidity_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="Liquidity Service not initialized")
    return service

@router.get("/{stock_code}/liquidity", response_model=LiquidityResponse)
async def get_stock_liquidity(
    stock_code: str = Path(..., description="股票代码"),
    request: Request = None
):
    """
    获取股票流动性数据 (API 3)
    包括:
    - 20日日均成交额
    - 买卖价差
    - 5档盘口(模拟/实时)
    """
    service = get_liquidity_service(request)
    try:
        metrics = await service.get_liquidity_metrics(stock_code)
        return LiquidityResponse(success=True, data=metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

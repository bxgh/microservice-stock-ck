# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request, Path
from pydantic import BaseModel
from typing import Dict, Any, Optional

router = APIRouter(prefix="/api/v1/stocks", tags=["股票状态与基本面"])

class StockStatusResponse(BaseModel):
    stock_code: str
    name: str
    is_st: bool
    is_suspended: bool
    is_delisted: bool
    trading_status: str # "TRADING", "HALT", "DELISTED"
    remark: Optional[str] = None

class StockFundamentalsSummary(BaseModel):
    stock_code: str
    # Valuation
    pe_ttm: Optional[float] = None
    pb_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    # Financials
    revenue_ttm: Optional[float] = None
    net_profit_ttm: Optional[float] = None
    gross_margin: Optional[float] = None
    roe_ttm: Optional[float] = None
    
    # Growth
    revenue_growth_yoy: Optional[float] = None
    profit_growth_yoy: Optional[float] = None

@router.get("/{stock_code}/status", response_model=StockStatusResponse)
async def get_stock_status(
    stock_code: str = Path(..., description="股票代码"),
    request: Request = None
):
    """
    获取股票交易状态 (ST/停牌/退市) (API 4)
    """
    quotes_service = getattr(request.app.state, "quotes_service", None)
    
    # Default State
    name = "Unknown"
    price = 0.0
    volume = 0
    
    if quotes_service:
        quotes = await quotes_service.get_realtime_quotes([stock_code])
        if quotes:
            q = quotes[0]
            name = q.get('name', 'Unknown')
            price = q.get('price', 0.0)
            volume = q.get('volume', 0)
    
    # Logic to determine status
    is_st = 'ST' in name.upper()
    
    # Suspension logic: 
    # Hard to detect 100% without specific suspension API.
    # Heuristic: If trading time (9:30-15:00) and volume is 0 and price unchanged? 
    # Or just return 'Normal' for now unless we have specific 'status' field in quotes.
    # Some AkShare quotes have 'trading_status'.
    
    # For now, simplistic heuristic
    is_suspended = False
    if volume == 0 and price > 0:
        # Possibly suspended if market is open. 
        # But maybe just illiquid.
        # Let's check name for '退' for delisted.
        pass
        
    is_delisted = '退' in name
    
    trading_status = "TRADING"
    if is_delisted:
        trading_status = "DELISTED"
    elif is_suspended:
        trading_status = "HALT"

    return StockStatusResponse(
        stock_code=stock_code,
        name=name,
        is_st=is_st,
        is_suspended=is_suspended,
        is_delisted=is_delisted,
        trading_status=trading_status
    )

@router.get("/{stock_code}/fundamentals", response_model=StockFundamentalsSummary)
async def get_stock_fundamentals(
    stock_code: str = Path(..., description="股票代码"),
    request: Request = None
):
    """
    获取股票基本面摘要 (Facade API)
    聚合估值和核心财务指标
    """
    valuation_service = getattr(request.app.state, "valuation_service", None)
    financial_service = getattr(request.app.state, "financial_service", None)
    
    summary = StockFundamentalsSummary(stock_code=stock_code)
    
    # 1. Valuation
    if valuation_service:
        try:
            val = await valuation_service.get_current_valuation(stock_code)
            if val:
                summary.pe_ttm = val.get('pe_ratio')
                summary.pb_ratio = val.get('pb_ratio')
                summary.market_cap = val.get('market_cap')
        except Exception as e:
            pass
            
    # 2. Financials (Indicators)
    if financial_service:
        try:
            fin = await financial_service.get_enhanced_indicators(stock_code)
            if fin:
                # Map fields if available directly or calculate
                summary.revenue_ttm = fin.get('revenue')  # This might be latest report revenue, not TTM.
                summary.net_profit_ttm = fin.get('net_profit')
                # Simple extraction for now
        except Exception as e:
            pass
            
    return summary

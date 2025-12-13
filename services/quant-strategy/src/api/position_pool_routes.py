"""
Position Pool API Routes

Provides endpoints for managing active positions and performing liquidity checks.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.stock_pool.position_pool_service import position_pool_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pools/position", tags=["Position Pool"])


class PositionCreateRequest(BaseModel):
    code: str
    name: str
    entry_price: float
    quantity: int
    strategy_type: str = "swing"  # 'long_term' or 'swing'
    stop_loss: Optional[float] = None


class PositionResponse(BaseModel):
    id: int
    code: str
    name: str
    quantity: int
    entry_price: float
    current_value: float
    profit_loss_pct: float
    liquidity_impact: str
    avg_daily_volume: Optional[float]


class LiquidityCheckRequest(BaseModel):
    code: str
    quantity: int
    price: float


class LiquidityCheckResponse(BaseModel):
    impact_level: str
    warning_message: str
    avg_daily_volume: float


@router.post("", response_model=PositionResponse)
async def add_position(position: PositionCreateRequest):
    """
    添加新持仓
    
    会自动进行流动性检查，并在日志中记录风险。
    """
    try:
        await position_pool_service.initialize()
        new_pos = await position_pool_service.add_position(
            code=position.code,
            name=position.name,
            entry_price=position.entry_price,
            quantity=position.quantity,
            strategy_type=position.strategy_type,
            stop_loss=position.stop_loss
        )
        return PositionResponse(
            id=new_pos.id,
            code=new_pos.code,
            name=new_pos.name,
            quantity=new_pos.quantity,
            entry_price=new_pos.entry_price,
            current_value=new_pos.current_value,
            profit_loss_pct=new_pos.profit_loss_pct,
            liquidity_impact=new_pos.liquidity_impact,
            avg_daily_volume=new_pos.avg_daily_volume
        )
    except Exception as e:
        logger.error(f"Failed to add position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[PositionResponse])
async def get_positions():
    """获取所有持仓"""
    try:
        await position_pool_service.initialize()
        positions = await position_pool_service.get_all_positions()
        return [
            PositionResponse(
                id=p.id,
                code=p.code,
                name=p.name,
                quantity=p.quantity,
                entry_price=p.entry_price,
                current_value=p.current_value or (p.quantity * p.entry_price),
                profit_loss_pct=p.profit_loss_pct or 0.0,
                liquidity_impact=p.liquidity_impact or "UNKNOWN",
                avg_daily_volume=p.avg_daily_volume
            ) for p in positions
        ]
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/liquidity-check", response_model=LiquidityCheckResponse)
async def check_liquidity(request: LiquidityCheckRequest):
    """
    交易前流动性检查
    
    评估拟交易金额对盘面的冲击风险。
    """
    try:
        await position_pool_service.initialize()
        impact, msg, vol = await position_pool_service.check_liquidity_risk(
            request.code, request.quantity, request.price
        )
        return LiquidityCheckResponse(
            impact_level=impact,
            warning_message=msg,
            avg_daily_volume=vol
        )
    except Exception as e:
        logger.error(f"Liquidity check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

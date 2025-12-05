from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Dict, Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stock-pool", tags=["Stock Pool"])

class ManualAddRequest(BaseModel):
    code: str
    duration: int = 60  # minutes

@router.post("/manual-add")
async def add_manual_stock(request: Request, body: ManualAddRequest):
    """
    手动添加股票到监控池
    """
    dynamic_manager = getattr(request.app.state, "dynamic_manager", None)
    if not dynamic_manager:
        raise HTTPException(status_code=503, detail="DynamicPoolManager not initialized")
        
    await dynamic_manager.add_manual(body.code, body.duration)
    return {"message": f"已添加 {body.code}, 持续 {body.duration} 分钟"}

@router.delete("/manual-remove/{code}")
async def remove_manual_stock(request: Request, code: str):
    """
    移除手动添加的股票
    """
    dynamic_manager = getattr(request.app.state, "dynamic_manager", None)
    if not dynamic_manager:
        raise HTTPException(status_code=503, detail="DynamicPoolManager not initialized")
        
    await dynamic_manager.remove_manual(code)
    return {"message": f"已移除 {code}"}

@router.get("/dynamic-stats")
async def get_dynamic_stats(request: Request):
    """
    获取动态池统计信息
    """
    dynamic_manager = getattr(request.app.state, "dynamic_manager", None)
    if not dynamic_manager:
        raise HTTPException(status_code=503, detail="DynamicPoolManager not initialized")
        
    return await dynamic_manager.get_stats()

@router.get("/promoted-list")
async def get_promoted_list(request: Request):
    """
    获取当前晋升的股票列表
    """
    dynamic_manager = getattr(request.app.state, "dynamic_manager", None)
    if not dynamic_manager:
        raise HTTPException(status_code=503, detail="DynamicPoolManager not initialized")
        
    stats = await dynamic_manager.get_stats()
    return stats.get("promoted_list", [])

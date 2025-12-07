from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Dict, Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stock-pool", tags=["Stock Pool"])

class ManualAddRequest(BaseModel):
    code: str
    name: str = ""
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


# ======== Promotion Monitor Endpoints (Story 004.03) ========

@router.post("/promotion/force-scan")
async def force_promotion_scan(request: Request):
    """
    强制触发一次飙升榜扫描，立即晋升热门股票
    """
    promotion_monitor = getattr(request.app.state, "promotion_monitor", None)
    if not promotion_monitor:
        raise HTTPException(status_code=503, detail="PromotionMonitor not initialized")
    
    await promotion_monitor.force_scan()
    return {"message": "扫描完成", "stats": promotion_monitor.get_stats()}

@router.get("/promotion/monitor-stats")
async def get_promotion_monitor_stats(request: Request):
    """
    获取晋升监控器统计信息
    """
    promotion_monitor = getattr(request.app.state, "promotion_monitor", None)
    if not promotion_monitor:
        raise HTTPException(status_code=503, detail="PromotionMonitor not initialized")
    
    return promotion_monitor.get_stats()

@router.post("/promotion/start")
async def start_promotion_monitor(request: Request):
    """
    启动晋升监控器
    """
    promotion_monitor = getattr(request.app.state, "promotion_monitor", None)
    if not promotion_monitor:
        raise HTTPException(status_code=503, detail="PromotionMonitor not initialized")
    
    await promotion_monitor.start()
    return {"message": "晋升监控器已启动"}

@router.post("/promotion/stop")
async def stop_promotion_monitor(request: Request):
    """
    停止晋升监控器
    """
    promotion_monitor = getattr(request.app.state, "promotion_monitor", None)
    if not promotion_monitor:
        raise HTTPException(status_code=503, detail="PromotionMonitor not initialized")
    
    await promotion_monitor.stop()
    return {"message": "晋升监控器已停止"}


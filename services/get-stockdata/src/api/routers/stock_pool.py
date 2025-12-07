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


# ======== Auto-Scaler Endpoints (US-004.04) ========

@router.get("/scaling/status")
async def get_scaling_status(request: Request):
    """
    获取自动扩容器状态
    
    返回当前层级、容量、自动模式状态、冷却状态等信息
    """
    auto_scaler = getattr(request.app.state, "auto_scaler", None)
    if not auto_scaler:
        raise HTTPException(status_code=503, detail="AutoScaler not initialized")
    
    return auto_scaler.get_stats()


@router.post("/scaling/scale-up")
async def manual_scale_up(
    request: Request, 
    force: bool = Query(False, description="是否强制扩容（忽略冷却期）")
):
    """
    手动触发扩容
    
    将股票池容量提升到下一个层级
    """
    auto_scaler = getattr(request.app.state, "auto_scaler", None)
    if not auto_scaler:
        raise HTTPException(status_code=503, detail="AutoScaler not initialized")
    
    success = await auto_scaler.scale_up(force=force)
    if success:
        return {
            "success": True,
            "message": f"扩容成功，当前容量: {auto_scaler.get_current_capacity()}",
            "stats": auto_scaler.get_stats()
        }
    else:
        raise HTTPException(status_code=400, detail="扩容失败，可能已达最大容量或在冷却期内")


@router.post("/scaling/scale-down")
async def manual_scale_down(
    request: Request,
    force: bool = Query(False, description="是否强制缩容")
):
    """
    手动触发缩容
    
    将股票池容量降低到上一个层级
    """
    auto_scaler = getattr(request.app.state, "auto_scaler", None)
    if not auto_scaler:
        raise HTTPException(status_code=503, detail="AutoScaler not initialized")
    
    success = await auto_scaler.scale_down(force=force)
    if success:
        return {
            "success": True,
            "message": f"缩容成功，当前容量: {auto_scaler.get_current_capacity()}",
            "stats": auto_scaler.get_stats()
        }
    else:
        raise HTTPException(status_code=400, detail="缩容失败，可能已达最小容量或在冷却期内")


@router.post("/scaling/set-tier/{tier}")
async def set_scaling_tier(request: Request, tier: int):
    """
    手动设置扩容层级
    
    Args:
        tier: 目标层级 (0-5)，对应容量: 0=100, 1=150, 2=200, 3=300, 4=500, 5=800
    """
    auto_scaler = getattr(request.app.state, "auto_scaler", None)
    if not auto_scaler:
        raise HTTPException(status_code=503, detail="AutoScaler not initialized")
    
    success = await auto_scaler.set_tier(tier)
    if success:
        return {
            "success": True,
            "message": f"层级设置成功，当前容量: {auto_scaler.get_current_capacity()}",
            "stats": auto_scaler.get_stats()
        }
    else:
        raise HTTPException(status_code=400, detail=f"无效的层级: {tier}")


@router.put("/scaling/auto-mode")
async def toggle_auto_mode(
    request: Request,
    enabled: bool = Query(..., description="是否启用自动扩容")
):
    """
    开关自动扩容模式
    
    启用后，系统会自动根据健康指标调整池大小
    """
    auto_scaler = getattr(request.app.state, "auto_scaler", None)
    if not auto_scaler:
        raise HTTPException(status_code=503, detail="AutoScaler not initialized")
    
    auto_scaler.set_auto_mode(enabled)
    return {
        "success": True,
        "message": f"自动扩容模式已{'开启' if enabled else '关闭'}",
        "auto_mode": enabled
    }


@router.post("/scaling/check")
async def check_scale_conditions(request: Request):
    """
    手动检查扩容条件
    
    返回当前是否满足扩容/缩容条件
    """
    auto_scaler = getattr(request.app.state, "auto_scaler", None)
    if not auto_scaler:
        raise HTTPException(status_code=503, detail="AutoScaler not initialized")
    
    decision = await auto_scaler.check_scale_conditions()
    return {
        "should_scale": decision.should_scale,
        "direction": decision.direction.value,
        "reason": decision.reason,
        "current_tier": decision.current_tier,
        "target_tier": decision.target_tier,
        "current_size": decision.current_size,
        "target_size": decision.target_size,
        "metrics": decision.metrics
    }

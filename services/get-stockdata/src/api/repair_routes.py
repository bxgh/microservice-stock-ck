"""
数据修复 API 路由 (已废弃)
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/repair", tags=["data-repair"])

@router.post("/stock/{stock_code}")
async def rebuild_stock(stock_code: str):
    raise HTTPException(status_code=410, detail="数据修复与重建功能已被移除，统一迁移至云端 8004 端口。")

@router.post("/batch")
async def rebuild_batch():
    raise HTTPException(status_code=410, detail="批量个股重建已被移除，请联系云端管理服务器处理。")

@router.get("/stock/{stock_code}/status")
async def get_rebuild_status(stock_code: str):
    raise HTTPException(status_code=410, detail="查询功能已随修复接口一并移除。")

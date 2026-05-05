from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/sync", tags=["synchronization"])

@router.get("/kline/status")
async def get_sync_status():
    raise HTTPException(status_code=410, detail="同步状态获取已迁移至云端 (Port 8004)，当前节点不再提供拉取服务。")

@router.get("/kline/history")
async def get_sync_history(limit: int = 7):
    raise HTTPException(status_code=410, detail="同步历史记录查询已迁移至云端 (Port 8004)。")

@router.post("/kline")
async def sync_kline_data():
    raise HTTPException(status_code=410, detail="同步任务发布已迁移至腾讯云。当前节点已被隔离为只读网关。")

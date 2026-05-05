from fastapi import APIRouter
from datetime import datetime
from ..config.settings import settings

health_router = APIRouter(prefix="/api/v1", tags=["System"])

@health_router.get("/health")
async def health_check():
    """
    系统健康检查
    """
    return {
        "status": "healthy",
        "service": settings.NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now().isoformat(),
        "env": settings.ENV
    }

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.core.config import settings

router = APIRouter()

@router.get("/health", summary="健康检查接口")
async def health_check():
    """
    健康检查端点。
    返回服务基础信息与状态，用于 Nacos 或容器管弦系统(docker-compose/k8s)的探针检测。
    """
    return JSONResponse(
        content={
            "status": "UP",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
        }
    )

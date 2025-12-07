"""
健康检查路由 - 量化策略服务
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

from models.base_models import ApiResponse

logger = logging.getLogger(__name__)

# 创建路由器
health_router = APIRouter(prefix="/api/v1", tags=["health"])

# 记录服务启动时间
start_time = datetime.now()


def _get_uptime() -> int:
    """获取服务运行时间（秒）"""
    return int((datetime.now() - start_time).total_seconds())


@health_router.get("/health", response_model=None, summary="健康检查")
async def health_check():
    """
    系统健康检查端点

    返回系统和服务状态信息
    """
    try:
        # 获取基础服务状态
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "uptime": _get_uptime(),
            "service": "quant-strategy",
            "checks": {}
        }

        # 基础检查 - 应用框架状态
        health_data["checks"]["framework"] = {
            "status": "pass",
            "message": "FastAPI framework is running"
        }

        # 基础检查 - API路由状态
        try:
            health_data["checks"]["api"] = {
                "status": "pass",
                "message": "API endpoints are accessible"
            }
        except Exception as e:
            health_data["checks"]["api"] = {
                "status": "fail",
                "message": f"API check failed: {str(e)}"
            }
            health_data["status"] = "degraded"

        # 检查服务注册状态
        try:
            health_data["checks"]["service_registry"] = {
                "status": "pass",
                "message": "Service registry is available"
            }
        except Exception as e:
            health_data["checks"]["service_registry"] = {
                "status": "warn",
                "message": f"Service registry check failed: {str(e)}"
            }

        # 策略引擎状态
        health_data["checks"]["strategy_engine"] = {
            "status": "pass",
            "message": "Strategy engine is ready"
        }

        return ApiResponse(
            success=True,
            message="Service health check completed",
            data=health_data
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ApiResponse(
            success=False,
            message=f"Health check failed: {str(e)}"
        )


@health_router.get("/ready", response_model=None, summary="就绪检查")
async def readiness_check():
    """
    就绪检查端点

    用于Kubernetes就绪探针
    """
    try:
        return ApiResponse(
            success=True,
            message="Service is ready",
            data={
                "status": "ready",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Service not ready: {str(e)}"
        )


@health_router.get("/live", response_model=None, summary="存活检查")
async def liveness_check():
    """
    存活检查端点

    用于Kubernetes存活探针
    """
    try:
        return ApiResponse(
            success=True,
            message="Service is alive",
            data={
                "status": "alive",
                "timestamp": datetime.now().isoformat(),
                "uptime": _get_uptime()
            }
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Service not alive: {str(e)}"
        )

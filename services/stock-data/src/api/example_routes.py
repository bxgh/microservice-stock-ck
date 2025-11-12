"""
示例API路由 - 可以复制用于创建新的业务路由
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter

from models.base_models import ApiResponse

logger = logging.getLogger(__name__)

# 创建路由器 - 复制此模板创建新的业务路由
example_router = APIRouter(prefix="/api/v1/example", tags=["example"])


@example_router.get("/", response_model=None, summary="示例端点")
async def example_endpoint():
    """
    示例API端点

    这是一个模板，可以复制用于创建新的业务逻辑
    """
    try:
        return ApiResponse(
            success=True,
            message="示例API正常工作",
            data={
                "message": "这是一个空白微服务模板",
                "timestamp": datetime.now().isoformat(),
                "service": "microservice-template"
            }
        )

    except Exception as e:
        logger.error(f"示例API失败: {e}")
        return ApiResponse(
            success=False,
            message=f"示例API失败: {str(e)}"
        )
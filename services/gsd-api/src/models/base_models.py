"""
基础数据模型
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationInfo(BaseModel):
    """分页信息模型"""
    total: int = Field(..., description="总数量")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="返回数量")
    has_more: bool = Field(..., description="是否有更多数据")


class HealthStatus(BaseModel):
    """健康状态模型"""
    status: str
    timestamp: datetime
    version: str
    uptime: int
    checks: Dict[str, Any]

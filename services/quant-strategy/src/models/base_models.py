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


class HealthStatus(BaseModel):
    """健康状态模型"""
    status: str
    timestamp: datetime
    version: str
    uptime: int
    checks: Dict[str, Any]

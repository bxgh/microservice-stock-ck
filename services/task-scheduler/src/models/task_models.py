"""
任务相关数据模型
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PAUSED = "paused"


class TaskDefinition(BaseModel):
    """任务定义模型"""
    name: str = Field(..., description="任务名称")
    task_type: str = Field(..., description="任务类型")
    description: Optional[str] = Field(None, description="任务描述")
    enabled: bool = Field(True, description="是否启用")

    # 调度配置
    cron_expression: Optional[str] = Field(None, description="Cron表达式")
    interval_seconds: Optional[int] = Field(None, description="间隔秒数")
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")

    # 执行配置
    timeout: int = Field(300, description="超时时间(秒)")
    max_retries: int = Field(3, description="最大重试次数")
    retry_delay: int = Field(60, description="重试延迟(秒)")

    # 任务配置
    config: Dict[str, str] = Field(default_factory=dict, description="任务配置")
    tags: List[str] = Field(default_factory=list, description="标签")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @validator('cron_expression')
    def validate_cron(cls, v, values):
        if v is not None:
            try:
                from apscheduler.triggers.cron import CronTrigger
                CronTrigger.from_crontab(v)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {e}")
        return v

    @validator('interval_seconds')
    def validate_interval(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError("Interval seconds must be positive")
        return v


class TaskExecution(BaseModel):
    """任务执行记录模型"""
    execution_id: str
    task_id: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
    result: Optional[str]
    error: Optional[str]
    retry_count: int
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TaskInfo(BaseModel):
    """任务信息模型"""
    task_id: str
    definition: TaskDefinition
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    last_execution: Optional[TaskExecution]
    next_run_time: Optional[datetime]
    execution_count: int
    success_count: int
    failure_count: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    tasks: List[TaskInfo]
    total: int
    page: int
    page_size: int


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
    uptime: Optional[int] = None
    checks: Dict[str, str]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ServiceStats(BaseModel):
    """服务统计模型"""
    total_jobs: int
    active_jobs: int
    paused_jobs: int
    plugins: List[str]
    scheduler_running: bool
    total_executions: int
    recent_success_rate: float
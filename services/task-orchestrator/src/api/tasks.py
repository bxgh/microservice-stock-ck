"""
任务管理 API 端点
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class TaskInfo(BaseModel):
    """任务信息"""
    id: str
    name: str
    enabled: bool
    schedule_type: str
    schedule_expression: str
    next_run_time: Optional[str] = None
    last_run_status: Optional[str] = None


class TaskHistory(BaseModel):
    """任务执行历史"""
    id: int
    task_id: str
    task_name: str
    status: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[int]
    exit_code: Optional[int]
    error_message: Optional[str]


class TaskStats(BaseModel):
    """任务统计"""
    task_id: str
    task_name: str
    total_executions: int
    successful: int
    failed: int
    success_rate: float
    avg_duration_seconds: Optional[float]
    last_run_time: Optional[str]


@router.get("/tasks", response_model=List[TaskInfo])
async def list_tasks():
    """
    获取所有任务列表
    """
    from main import task_config, scheduler
    
    if not task_config:
        raise HTTPException(status_code=500, detail="Task configuration not loaded")
    
    tasks = []
    for task_def in task_config.tasks:
        # 从 scheduler 获取下一次运行时间
        job = scheduler.get_job(task_def.id)
        next_run = str(job.next_run_time) if job else None
        
        tasks.append(TaskInfo(
            id=task_def.id,
            name=task_def.name,
            enabled=task_def.enabled,
            schedule_type=task_def.schedule.type.value,
            schedule_expression=task_def.schedule.expression or "",
            next_run_time=next_run,
            last_run_status=None  # TODO: 从数据库查询
        ))
    
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskInfo)
async def get_task(task_id: str):
    """
    获取任务详情
    """
    from main import task_config, scheduler
    
    if not task_config:
        raise HTTPException(status_code=500, detail="Task configuration not loaded")
    
    task_def = next((t for t in task_config.tasks if t.id == task_id), None)
    if not task_def:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    
    job = scheduler.get_job(task_id)
    next_run = str(job.next_run_time) if job else None
    
    return TaskInfo(
        id=task_def.id,
        name=task_def.name,
        enabled=task_def.enabled,
        schedule_type=task_def.schedule.type.value,
        schedule_expression=task_def.schedule.expression or "",
        next_run_time=next_run
    )


@router.post("/tasks/{task_id}/trigger")
async def trigger_task(task_id: str):
    """
    手动触发任务
    """
    from main import scheduler
    
    job = scheduler.get_job(task_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found or not registered")
    
    # 手动触发任务
    job.modify(next_run_time=None)  # 立即执行
    scheduler.modify_job(task_id, next_run_time=None)
    
    return {"status": "triggered", "task_id": task_id}


@router.get("/tasks/{task_id}/history", response_model=List[TaskHistory])
async def get_task_history(task_id: str, limit: int = 20):
    """
    获取任务执行历史
    """
    from main import task_logger
    
    if not task_logger:
        raise HTTPException(status_code=500, detail="Task logger not initialized")
    
    rows = await task_logger.get_task_history(task_id, limit)
    
    return [
        TaskHistory(
            id=row['id'],
            task_id=row['task_id'],
            task_name=row['task_name'],
            status=row['status'],
            start_time=str(row['start_time']),
            end_time=str(row['end_time']) if row['end_time'] else None,
            duration_seconds=row['duration_seconds'],
            exit_code=row['exit_code'],
            error_message=row['error_message']
        )
        for row in rows
    ]


@router.get("/tasks/{task_id}/stats", response_model=TaskStats)
async def get_task_stats(task_id: str):
    """
    获取任务统计信息
    """
    from main import task_logger
    
    if not task_logger:
        raise HTTPException(status_code=500, detail="Task logger not initialized")
    
    stats = await task_logger.get_task_stats(task_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"No statistics found for task '{task_id}'")
    
    return TaskStats(**stats)


@router.post("/reload")
async def reload_config():
    """
    重新加载配置
    """
    # TODO: 实现配置热重载
    raise HTTPException(status_code=501, detail="Configuration reload not implemented yet")

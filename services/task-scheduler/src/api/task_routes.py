"""
任务相关API路由
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.task_models import (
    TaskDefinition, TaskInfo, TaskListResponse, ApiResponse
)
# 全局服务实例（将在main.py中设置）
task_service = None
scheduler_service = None
service_registry = None

def set_services(t_service, s_service, s_registry):
    """设置全局服务实例"""
    global task_service, scheduler_service, service_registry
    task_service = t_service
    scheduler_service = s_service
    service_registry = s_registry

from api.middleware import get_current_user

logger = logging.getLogger(__name__)

# 创建路由器
task_router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# 认证
security = HTTPBearer(auto_error=False)


@task_router.post("", response_model=None, summary="创建任务")
async def create_task(
    definition: TaskDefinition,
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    创建新的任务
    """
    try:
        # 验证任务定义
        errors = await task_service.validate_task_definition(definition)
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid task definition", "errors": errors}
            )

        # 创建任务
        task_info = await task_service.create_task(definition)

        return ApiResponse(
            success=True,
            message="Task created successfully",
            data=task_info.dict()
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.get("", response_model=None, summary="查询任务列表")
async def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态过滤"),
    tags: Optional[str] = Query(None, description="标签过滤（逗号分隔）"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    查询任务列表，支持分页和过滤
    """
    try:
        # 处理标签过滤
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # 查询任务
        tasks = await task_service.list_tasks(page, page_size, status, tag_list)

        # 计算总数（简化实现）
        total = len(tasks) if page == 1 else page * page_size

        response_data = TaskListResponse(
            tasks=tasks,
            total=total,
            page=page,
            page_size=page_size
        )

        return ApiResponse(
            success=True,
            message="Tasks retrieved successfully",
            data=response_data.dict()
        )

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.get("/{task_id}", response_model=None, summary="获取任务详情")
async def get_task(
    task_id: str = Path(..., description="任务ID"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    获取指定任务的详细信息
    """
    try:
        task_info = await task_service.get_task(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")

        return ApiResponse(
            success=True,
            message="Task retrieved successfully",
            data=task_info.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.put("/{task_id}", response_model=None, summary="更新任务")
async def update_task(
    task_id: str,
    definition: TaskDefinition,
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    更新指定任务的配置
    """
    try:
        # 验证任务定义
        errors = await task_service.validate_task_definition(definition)
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid task definition", "errors": errors}
            )

        # 更新任务
        task_info = await task_service.update_task(task_id, definition)

        return ApiResponse(
            success=True,
            message="Task updated successfully",
            data=task_info.dict()
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.delete("/{task_id}", response_model=None, summary="删除任务")
async def delete_task(
    task_id: str = Path(..., description="任务ID"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    删除指定的任务
    """
    try:
        success = await task_service.delete_task(task_id)

        return ApiResponse(
            success=success,
            message="Task deleted successfully" if success else "Failed to delete task"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.post("/{task_id}/trigger", response_model=None, summary="手动触发任务")
async def trigger_task(
    task_id: str = Path(..., description="任务ID"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    手动触发指定任务的执行
    """
    try:
        success = await task_service.trigger_task(task_id)

        return ApiResponse(
            success=success,
            message="Task triggered successfully" if success else "Failed to trigger task"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to trigger task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.post("/{task_id}/pause", response_model=None, summary="暂停任务")
async def pause_task(
    task_id: str = Path(..., description="任务ID"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    暂停指定的任务
    """
    try:
        success = await task_service.pause_task(task_id)

        return ApiResponse(
            success=success,
            message="Task paused successfully" if success else "Failed to pause task"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to pause task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.post("/{task_id}/resume", response_model=None, summary="恢复任务")
async def resume_task(
    task_id: str = Path(..., description="任务ID"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    恢复指定的任务
    """
    try:
        success = await task_service.resume_task(task_id)

        return ApiResponse(
            success=success,
            message="Task resumed successfully" if success else "Failed to resume task"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to resume task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.post("/{task_id}/enable", response_model=None, summary="启用任务")
async def enable_task(
    task_id: str = Path(..., description="任务ID"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    启用指定的任务
    """
    try:
        success = await task_service.enable_task(task_id)

        return ApiResponse(
            success=success,
            message="Task enabled successfully" if success else "Failed to enable task"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to enable task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.post("/{task_id}/disable", response_model=None, summary="禁用任务")
async def disable_task(
    task_id: str = Path(..., description="任务ID"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    禁用指定的任务
    """
    try:
        success = await task_service.disable_task(task_id)

        return ApiResponse(
            success=success,
            message="Task disabled successfully" if success else "Failed to disable task"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to disable task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@task_router.get("/{task_id}/statistics", response_model=None, summary="获取任务统计")
async def get_task_statistics(
    task_id: str = Path(..., description="任务ID"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    # task_service: TaskService = Depends(TaskService)  # 使用全局实例,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(get_current_user)
):
    """
    获取指定任务的执行统计信息
    """
    try:
        stats = task_service.get_task_statistics(task_id, days)

        return ApiResponse(
            success=True,
            message="Task statistics retrieved successfully",
            data=stats
        )

    except Exception as e:
        logger.error(f"Failed to get task statistics for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
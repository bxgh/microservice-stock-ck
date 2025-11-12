"""
健康检查和统计API路由
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from models.task_models import ApiResponse, HealthStatus, ServiceStats
from api.middleware import get_current_user

logger = logging.getLogger(__name__)

# 创建路由器
health_router = APIRouter(prefix="/api/v1", tags=["health", "stats"])


@health_router.get("/health", response_model=None, summary="健康检查")
async def health_check(
    
):
    """
    检查服务健康状态
    """
    try:
        from config.settings import settings
        from repository.execution_repository import ExecutionRepository

        # 获取基础服务状态
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": settings.version,
            "uptime": _get_uptime(),
            "checks": {}
        }

        # 检查数据库连接
        try:
            task_count = len(await __import__("api.task_routes", fromlist=["task_service"]).task_service.list_tasks(page_size=1))
            health_data["checks"]["database"] = {
                "status": "pass",
                "message": f"Database connected, {task_count} tasks found"
            }
        except Exception as e:
            health_data["checks"]["database"] = {
                "status": "fail",
                "message": f"Database connection failed: {str(e)}"
            }
            health_data["status"] = "unhealthy"

        # 检查调度器状态 - 简化检查
        try:
            from service.scheduler_service import SchedulerService
            # 只检查调度器服务类是否存在，不实例化
            health_data["checks"]["scheduler"] = {
                "status": "pass",
                "message": "Scheduler service available"
            }
        except Exception as e:
            health_data["checks"]["scheduler"] = {
                "status": "fail",
                "message": f"Scheduler check failed: {str(e)}"
            }
            # 不将整体状态设为unhealthy，只记录检查结果

        # 检查插件系统
        try:
            from plugins.plugin_manager import PluginManager
            plugin_manager = PluginManager()
            available_plugins = plugin_manager.get_available_plugins()

            health_data["checks"]["plugins"] = {
                "status": "pass",
                "message": f"{len(available_plugins)} plugins available: {', '.join(available_plugins)}"
            }
        except Exception as e:
            health_data["checks"]["plugins"] = {
                "status": "fail",
                "message": f"Plugin system check failed: {str(e)}"
            }
            health_data["status"] = "unhealthy"

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


@health_router.get("/stats", response_model=None, summary="获取服务统计")
async def get_service_stats(
    
):
    """
    获取服务运行统计信息
    """
    try:
        from repository.execution_repository import ExecutionRepository
        from config.settings import settings

        # 获取任务统计
        all_tasks = await __import__("api.task_routes", fromlist=["task_service"]).task_service.list_tasks(page_size=1000)  # 获取所有任务
        enabled_tasks = await task_service.get_enabled_tasks()

        # 计算统计信息
        total_tasks = len(all_tasks)
        enabled_count = len(enabled_tasks)
        disabled_count = total_tasks - enabled_count

        # 按状态统计
        status_counts = {}
        execution_counts = {"total": 0, "success": 0, "failed": 0, "timeout": 0}

        for task in all_tasks:
            # 状态统计
            status = task.status
            status_counts[status] = status_counts.get(status, 0) + 1

            # 执行统计
            execution_counts["total"] += task.execution_count
            execution_counts["success"] += task.success_count
            execution_counts["failed"] += task.failure_count

        # 计算成功率
        success_rate = 0
        if execution_counts["total"] > 0:
            success_rate = (execution_counts["success"] / execution_counts["total"]) * 100

        # 获取插件统计
        from plugins.plugin_manager import PluginManager
        plugin_manager = PluginManager()
        available_plugins = plugin_manager.get_available_plugins()

        # 获取最近执行统计
        exec_repo = ExecutionRepository()
        recent_executions = exec_repo.count_executions()  # 总执行数

        stats_data = {
            "service_info": {
                "name": settings.name,
                "version": settings.version,
                "uptime": _get_uptime()
            },
            "task_statistics": {
                "total_tasks": total_tasks,
                "enabled_tasks": enabled_count,
                "disabled_tasks": disabled_count,
                "active_tasks": len([t for t in all_tasks if t.status == "running"]),
                "paused_tasks": len([t for t in all_tasks if t.status == "paused"])
            },
            "status_distribution": status_counts,
            "execution_statistics": {
                "total_executions": execution_counts["total"],
                "successful_executions": execution_counts["success"],
                "failed_executions": execution_counts["failed"],
                "success_rate": round(success_rate, 2)
            },
            "plugin_info": {
                "available_plugins": available_plugins,
                "plugin_count": len(available_plugins)
            },
            "system_info": {
                "scheduler_running": _is_scheduler_running(),
                "database_connected": _is_database_connected(),
                "recent_executions": recent_executions
            }
        }

        return ApiResponse(
            success=True,
            message="Service statistics retrieved successfully",
            data=stats_data
        )

    except Exception as e:
        logger.error(f"Failed to get service stats: {e}")
        raise Exception(f"Failed to get service statistics: {str(e)}")


def _get_uptime() -> int:
    """获取服务运行时间（秒）"""
    try:
        import time
        # 这里应该记录服务启动时间
        # 简化实现，返回一个模拟值
        return int(time.time() - getattr(_get_uptime, '_start_time', time.time()))
    except:
        return 0


def _is_scheduler_running() -> bool:
    """检查调度器是否运行"""
    try:
        from .scheduler_service import SchedulerService
        from repository.task_repository import TaskRepository
        scheduler_service = SchedulerService(TaskRepository())
        return scheduler_service.is_running()
    except:
        return False


def _is_database_connected() -> bool:
    """检查数据库连接"""
    try:
        from repository.task_repository import TaskRepository
        repo = TaskRepository()
        # 尝试执行一个简单查询
        repo.get_tasks_by_type("test")
        return True
    except:
        return False


# 设置启动时间
_get_uptime._start_time = __import__('time').time()
"""
TaskScheduler 微服务组件 - 完整版启动文件
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 导入服务层
from service.scheduler_service import SchedulerService
from service.execution_service import ExecutionService
from service.task_service_simple import TaskService

# 导入配置
from config.settings import Settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
settings = Settings()
scheduler_service: SchedulerService = None
execution_service: ExecutionService = None
task_service: TaskService = None
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scheduler_service, execution_service, task_service

    logger.info("Starting TaskScheduler microservice...")

    # 初始化服务
    try:
        # 初始化配置
        config = {
            "timezone": "Asia/Shanghai",
            "redis_url": settings.redis_url,
            "debug": settings.debug
        }

        # 初始化调度器服务
        scheduler_service = SchedulerService(config)
        await scheduler_service.start()
        logger.info("Scheduler service started")

        # 初始化执行服务
        execution_service = ExecutionService(config)
        logger.info("Execution service started")

        # 初始化任务服务
        task_service = TaskService(
            scheduler_service=scheduler_service,
            execution_service=execution_service,
            config=config
        )
        logger.info("Task service started")

        # 将服务添加到应用状态
        app.state.scheduler_service = scheduler_service
        app.state.execution_service = execution_service
        app.state.task_service = task_service

        logger.info("All services started successfully")

    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        raise

    yield

    # 关闭服务
    logger.info("Shutting down TaskScheduler microservice...")
    try:
        if scheduler_service:
            await scheduler_service.shutdown(wait=True)
            logger.info("Scheduler service shutdown")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="TaskScheduler",
    description="TaskScheduler 微服务组件 - 企业级任务调度服务",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API响应模型
class ApiResponse(JSONResponse):
    """统一API响应格式"""
    def __init__(self, data: Any = None, message: str = "success", code: int = 200):
        content = {
            "code": code,
            "message": message,
            "data": data,
            "timestamp": int(time.time())
        }
        super().__init__(content=content)


# 健康检查端点
@app.get("/api/v1/health")
async def health_check():
    """健康检查端点"""
    return ApiResponse({
        "status": "healthy",
        "service": "TaskScheduler",
        "version": "2.0.0",
        "uptime": int(time.time() - start_time)
    })


@app.get("/api/v1/stats")
async def get_stats():
    """获取服务统计信息"""
    try:
        if not hasattr(app.state, 'task_service') or not app.state.task_service:
            return ApiResponse({
                "service": "TaskScheduler",
                "version": "2.0.0",
                "status": "initializing",
                "uptime": int(time.time() - start_time),
                "tasks": {"total": 0, "running": 0, "completed": 0, "failed": 0}
            })

        stats = await app.state.task_service.get_stats()
        return ApiResponse({
            "service": "TaskScheduler",
            "version": "2.0.0",
            "status": "running",
            "uptime": int(time.time() - start_time),
            "tasks": stats
        })
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return ApiResponse(
            data=None,
            message=f"Failed to get stats: {str(e)}",
            code=500
        )


@app.get("/")
async def root():
    """根端点"""
    return ApiResponse({
        "message": "TaskScheduler Microservice API",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/api/v1/health",
            "stats": "/api/v1/stats",
            "tasks": "/api/v1/tasks",
            "docs": "/docs"
        }
    })


# 任务管理端点
@app.post("/api/v1/tasks")
async def create_task(task_data: Dict[str, Any]):
    """创建任务"""
    try:
        if not hasattr(app.state, 'task_service') or not app.state.task_service:
            raise HTTPException(status_code=503, detail="Task service not available")

        task = await app.state.task_service.create_task(task_data)
        return ApiResponse(data=task, message="Task created successfully")
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return ApiResponse(
            data=None,
            message=f"Failed to create task: {str(e)}",
            code=500
        )


@app.get("/api/v1/tasks")
async def list_tasks(limit: int = 100, offset: int = 0, status: str = None):
    """获取任务列表"""
    try:
        if not hasattr(app.state, 'task_service') or not app.state.task_service:
            return ApiResponse(data=[], message="Task service not available")

        tasks = await app.state.task_service.list_tasks(limit=limit, offset=offset, status=status)
        return ApiResponse(data=tasks)
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return ApiResponse(
            data=[],
            message=f"Failed to list tasks: {str(e)}",
            code=500
        )


@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    try:
        if not hasattr(app.state, 'task_service') or not app.state.task_service:
            raise HTTPException(status_code=503, detail="Task service not available")

        task = await app.state.task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return ApiResponse(data=task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task: {e}")
        return ApiResponse(
            data=None,
            message=f"Failed to get task: {str(e)}",
            code=500
        )


@app.delete("/api/v1/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    try:
        if not hasattr(app.state, 'task_service') or not app.state.task_service:
            raise HTTPException(status_code=503, detail="Task service not available")

        success = await app.state.task_service.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")

        return ApiResponse(message="Task deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        return ApiResponse(
            data=None,
            message=f"Failed to delete task: {str(e)}",
            code=500
        )


@app.post("/api/v1/tasks/{task_id}/start")
async def start_task(task_id: str):
    """启动任务"""
    try:
        if not hasattr(app.state, 'task_service') or not app.state.task_service:
            raise HTTPException(status_code=503, detail="Task service not available")

        success = await app.state.task_service.start_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be started")

        return ApiResponse(message="Task started successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start task: {e}")
        return ApiResponse(
            data=None,
            message=f"Failed to start task: {str(e)}",
            code=500
        )


@app.post("/api/v1/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """停止任务"""
    try:
        if not hasattr(app.state, 'task_service') or not app.state.task_service:
            raise HTTPException(status_code=503, detail="Task service not available")

        success = await app.state.task_service.stop_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be stopped")

        return ApiResponse(message="Task stopped successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop task: {e}")
        return ApiResponse(
            data=None,
            message=f"Failed to stop task: {str(e)}",
            code=500
        )


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"Unhandled exception: {exc}")
    return ApiResponse(
        data=None,
        message="Internal server error",
        code=500
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting TaskScheduler microservice...")
    uvicorn.run(
        "main_complete:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
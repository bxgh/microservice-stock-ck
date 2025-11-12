#!/usr/bin/env python3
"""
TaskScheduler 微服务组件 - 分层架构主文件

分层架构设计：
- API层：HTTP路由和请求处理
- Service层：业务逻辑处理
- Repository层：数据访问抽象
- Models层：数据模型定义
- Config层：配置管理
"""

import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager
import socket

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 导入分层组件
from config.settings import settings
from models.task_models import ApiResponse
from api.task_routes import task_router
from api.health_routes import health_router
from api.middleware import verify_api_key, add_cors_headers, log_requests
from repository.task_repository import TaskRepository
from repository.execution_repository import ExecutionRepository
from service.task_service import TaskService
from service.scheduler_service import SchedulerService
from plugins.plugin_manager import PluginManager

# 导入服务注册发现
from registry.nacos_registry_simple import initialize_nacos, register_to_nacos, cleanup_nacos

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_file)
    ]
)

logger = logging.getLogger(__name__)

# 全局服务实例
task_repository: TaskRepository = None
execution_repository: ExecutionRepository = None
plugin_manager: PluginManager = None
task_service: TaskService = None
scheduler_service: SchedulerService = None
service_registry = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时初始化
    await startup()
    yield
    # 关闭时清理
    await shutdown()


async def register_service_to_nacos():
    """注册服务到 Nacos"""
    try:
        nacos_url = os.getenv("NACOS_SERVER_URL", "http://localhost:8848")
        service_registry = await init_nacos_registry(nacos_url)

        # 获取本地IP
        import socket
        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return "127.0.0.1"

        local_ip = get_local_ip()
        port = settings.port

        # 创建服务实例
        service_instance = NacosServiceInstance(
            service_name="task-scheduler",
            ip=local_ip,
            port=port,
            cluster_name="DEFAULT",
            group_name="DEFAULT_GROUP",
            metadata={
                "version": settings.version,
                "environment": os.getenv("ENVIRONMENT", "development"),
                "description": "TaskScheduler 微服务 - 企业级任务调度服务",
                "service_id": f"task-scheduler-{os.urandom(4).hex()}",
                "framework": "FastAPI"
            },
            weight=1.0,
            enabled=True,
            healthy=True,
            ephemeral=True
        )

        # 注册服务
        success = await service_registry.register_service(service_instance)
        if success:
            logger.info(f"✅ 服务已注册到 Nacos: {service_instance.service_name}")
            logger.info(f"🌐 服务地址: http://{local_ip}:{port}")
        else:
            logger.error("❌ 服务注册失败")

        return service_registry
    except Exception as e:
        logger.error(f"❌ 服务注册过程中出错: {e}")
        return None


async def startup():
    """
    启动初始化
    """
    global task_repository, execution_repository, plugin_manager, task_service, scheduler_service, service_registry

    logger.info("Starting TaskScheduler microservice...")

    try:
        # 初始化数据访问层
        logger.info("Initializing repositories...")
        task_repository = TaskRepository(settings.database_path)
        execution_repository = ExecutionRepository(settings.database_path)
        logger.info("Repositories initialized successfully")

        # 初始化插件管理器
        logger.info("Initializing plugin manager...")
        plugin_manager = PluginManager()
        logger.info(f"Plugin manager initialized with {len(plugin_manager.get_available_plugins())} plugins")

        # 初始化服务层
        logger.info("Initializing services...")
        task_service = TaskService(task_repository, plugin_manager)
        # 将实例存储到全局变量
        globals()['task_service_instance'] = task_service
        # SchedulerService需要配置字典，不是repository
        scheduler_service = SchedulerService(settings.dict() if hasattr(settings, 'dict') else {})
        logger.info("Services initialized successfully")

        # 启动调度器
        logger.info("Starting scheduler...")
        await scheduler_service.start()
        logger.info("Scheduler started successfully")

        # 加载现有任务到调度器
        logger.info("Loading existing tasks to scheduler...")
        enabled_tasks = await task_service.get_enabled_tasks()
        loaded_count = 0
        for task in enabled_tasks:
            if scheduler_service.add_task(task):
                loaded_count += 1

        logger.info(f"Loaded {loaded_count} tasks to scheduler")

        # 设置API路由的全局服务实例
        from api.task_routes import set_services
        set_services(task_service, scheduler_service, None)
        logger.info("API services configured successfully")

        # 注册到 Nacos
        logger.info("Registering service to Nacos...")
        await initialize_nacos()
        success = await register_to_nacos(
            service_name="task-scheduler",
            service_port=settings.port,
            framework="FastAPI",
            description="TaskScheduler 微服务 - 企业级任务调度服务"
        )

        if success:
            logger.info("✅ 服务注册成功")
        else:
            logger.warning("❌ 服务注册失败，但服务继续运行")

        logger.info("TaskScheduler microservice started successfully")
        logger.info(f"Service running on http://{settings.host}:{settings.port}")
        logger.info(f"API documentation available at http://{settings.host}:{settings.port}/docs")

    except Exception as e:
        logger.error(f"Failed to start TaskScheduler: {e}")
        sys.exit(1)


async def shutdown():
    """
    关闭清理
    """
    global scheduler_service

    logger.info("Shutting down TaskScheduler microservice...")

    try:
        # 停止调度器
        if scheduler_service:
            logger.info("Stopping scheduler...")
            await scheduler_service.stop()
            logger.info("Scheduler stopped successfully")

        # 清理Nacos服务注册
        logger.info("Deregistering from Nacos...")
        await cleanup_nacos()
        logger.info("Nacos deregistration completed")

        logger.info("TaskScheduler microservice shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    创建FastAPI应用
    """
    app = FastAPI(
        title=settings.name,
        description="TaskScheduler 微服务组件 - 企业级任务调度服务",
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加自定义中间件
    app.middleware("http")(log_requests)
    app.middleware("http")(add_cors_headers)

    # 如果配置了API Key，添加验证中间件
    if settings.api_key:
        app.middleware("http")(verify_api_key)

    # 注册路由
    app.include_router(task_router)
    app.include_router(health_router)

    # 添加根路径
    @app.get("/", response_model=ApiResponse, tags=["root"])
    async def root():
        """根路径"""
        return ApiResponse(
            success=True,
            message=f"Welcome to {settings.name} v{settings.version}",
            data={
                "service": settings.name,
                "version": settings.version,
                "docs": "/docs",
                "health": "/api/v1/health",
                "stats": "/api/v1/stats"
            }
        )

    # 异常处理器
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return ApiResponse(
            success=False,
            message="Internal server error",
            data={"detail": str(exc)} if settings.debug else None
        )

    return app


def get_dependencies():
    """
    获取依赖注入实例
    """
    return {
        "task_repository": task_repository,
        "execution_repository": execution_repository,
        "plugin_manager": plugin_manager,
        "task_service": task_service,
        "scheduler_service": scheduler_service
    }


# 依赖注入提供者
def provide_task_repository() -> TaskRepository:
    return task_repository


def provide_execution_repository() -> ExecutionRepository:
    return execution_repository


def provide_plugin_manager() -> PluginManager:
    return plugin_manager


def provide_task_service() -> TaskService:
    return TaskService(task_repository, plugin_manager)


# 全局变量用于存储服务实例
task_service_instance = None


def main():
    """
    主函数
    """
    logger.info(f"Starting {settings.name} v{settings.version}")
    logger.info(f"Configuration: debug={settings.debug}, log_level={settings.log_level}")

    # 创建应用
    app = create_app()

    # 启动服务器
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        access_log=settings.access_log
    )


if __name__ == "__main__":
    main()
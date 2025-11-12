#!/usr/bin/env python3
"""
TaskScheduler 微服务组件 - 企业级启动文件
"""
import asyncio
import logging
import sys
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 导入服务注册发现
from registry.nacos_registry import NacosServiceInstance, init_nacos_registry

# 配置管理
from config.settings import settings

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# 全局服务注册实例
service_registry = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global service_registry
    logger.info("🚀 TaskScheduler 服务启动中...")

    # 启动初始化
    try:
        # 初始化服务注册发现
        nacos_url = os.getenv("NACOS_URL", "http://localhost:8848")
        service_registry = await init_nacos_registry(nacos_url)

        # 注册服务到 Nacos
        await register_service_to_nacos()

        # 初始化其他组件
        await initialize_components()

        logger.info("✅ TaskScheduler 服务启动完成")
        yield
    except Exception as e:
        logger.error(f"❌ TaskScheduler 服务启动失败: {e}")
        raise
    finally:
        logger.info("🛑 TaskScheduler 服务停止...")
        if service_registry:
            await service_registry.stop()


async def register_service_to_nacos():
    """注册服务到 Nacos"""
    try:
        # 获取服务实例信息
        local_ip = service_registry.get_local_ip()
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
                "service_id": f"task-scheduler-{uuid.uuid4().hex[:8]}"
            },
            weight=1.0,
            enabled=True,
            healthy=True,
            ephemeral=True
        )

        # 注册服务
        success = await service_registry.register_service(service_instance)
        if success:
            logger.info(f"📡 服务已注册到 Nacos: {service_instance.service_name}")
            logger.info(f"🌐 服务地址: http://{local_ip}:{port}")
        else:
            logger.error("❌ 服务注册失败")

    except Exception as e:
        logger.error(f"❌ 服务注册过程中出错: {e}")


async def initialize_components():
    """初始化其他组件"""
    try:
        # 这里可以初始化数据库连接、缓存等
        logger.info("🔧 初始化组件完成")
    except Exception as e:
        logger.error(f"❌ 组件初始化失败: {e}")
        raise


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="TaskScheduler 微服务组件 - 企业级任务调度服务",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查路由
@app.get("/api/v1/health")
async def health_check():
    """健康检查接口"""
    from datetime import datetime

    health_data = {
        "status": "healthy",
        "service": settings.name,
        "version": settings.version,
        "timestamp": datetime.now().isoformat(),
        "service_id": getattr(service_registry, 'local_service_id', None)
    }

    # 检查服务注册状态
    if service_registry and service_registry.local_service_id:
        health_data["registry_status"] = "registered"
    else:
        health_data["registry_status"] = "not_registered"

    return health_data


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    logger.info(f"🎯 启动 {settings.app_name} v{settings.app_version}")
    logger.info(f"🌐 服务地址: http://{settings.host}:{settings.port}")
    logger.info(f"📚 API 文档: http://{settings.host}:{settings.port}/docs")

    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else settings.workers
    )
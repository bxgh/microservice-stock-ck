#!/usr/bin/env python3
"""
微服务模板 - 空白框架

这是一个最小化的微服务模板，包含：
- 服务注册发现
- 健康检查
- 基础中间件
- 示例API路由

使用方法：
1. 复制此目录到新的服务名
2. 修改配置文件中的服务名和端口
3. 在 api/ 目录下创建新的业务路由
4. 在 models/ 目录下创建数据模型
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

# 导入核心组件
from config.settings import settings
from api.health_routes import health_router
from api.example_routes import example_router
from api.middleware import add_cors_headers, log_requests

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

# 全局变量
app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    try:
        await startup()
        yield
    finally:
        await shutdown()


async def startup():
    """
    服务启动初始化
    """
    global app

    logger.info(f"Starting {settings.name} v{settings.version}")
    logger.info(f"Configuration: debug={settings.debug}, log_level={settings.log_level}")

    try:
        logger.info("Starting microservice...")

        # 注册到 Nacos
        logger.info("Registering service to Nacos...")
        await initialize_nacos()
        success = await register_to_nacos(
            service_name=settings.name.lower().replace(" ", "-"),
            service_port=settings.port,
            framework="FastAPI",
            description=f"{settings.name} 微服务 - 基于模板创建"
        )

        if success:
            logger.info("✅ 服务注册成功")
        else:
            logger.warning("❌ 服务注册失败，但服务继续运行")

        logger.info("Microservice started successfully")
        logger.info(f"Service running on http://{settings.host}:{settings.port}")
        logger.info(f"API documentation available at http://{settings.host}:{settings.port}/docs")

    except Exception as e:
        logger.error(f"Failed to start microservice: {e}")
        sys.exit(1)


async def shutdown():
    """
    关闭清理
    """
    logger.info("Shutting down microservice...")

    try:
        # 清理Nacos服务注册
        logger.info("Deregistering from Nacos...")
        await cleanup_nacos()
        logger.info("Nacos deregistration completed")

        logger.info("Microservice shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    创建FastAPI应用
    """
    app = FastAPI(
        title=settings.name,
        description=f"{settings.name} 微服务 - 基于微服务模板创建",
        version=settings.version,
        lifespan=lifespan
    )

    # 添加中间件
    app.middleware("http")(add_cors_headers)
    app.middleware("http")(log_requests)

    # 注册路由
    app.include_router(health_router)
    app.include_router(example_router)  # 示例路由，可以删除或替换

    return app


def main():
    """
    主函数
    """
    global app
    app = create_app()

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=settings.access_log
    )


if __name__ == "__main__":
    main()
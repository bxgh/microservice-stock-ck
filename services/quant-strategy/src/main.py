#!/usr/bin/env python3
"""
量化策略微服务 - Quant Strategy Service

这是一个量化策略引擎的基础框架，包含：
- 服务注册发现
- 健康检查
- 基础中间件
- 策略管理API示例

后续将扩展支持：
- OFI (主动买卖单失衡策略)
- Smart Money (大单资金流向追踪)
- Order Book Pressure (盘口深度压力分析)
- VWAP (日内加权均价乖离策略)
- Liquidity Shock (流动性冲击监控)
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
from api.strategy_routes import strategy_router
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
        logger.info("Starting Quant Strategy microservice...")

        # 注册到 Nacos
        logger.info("Registering service to Nacos...")
        await initialize_nacos()
        success = await register_to_nacos(
            service_name=settings.name.lower().replace(" ", "-"),
            service_port=settings.port,
            framework="FastAPI",
            description=f"{settings.name} 微服务 - 量化策略引擎"
        )

        if success:
            logger.info("✅ 服务注册成功")
        else:
            logger.warning("❌ 服务注册失败，但服务继续运行")

        logger.info("Quant Strategy microservice started successfully")
        logger.info(f"Service running on http://{settings.host}:{settings.port}")
        logger.info(f"API documentation available at http://{settings.host}:{settings.port}/docs")

    except Exception as e:
        logger.error(f"Failed to start microservice: {e}")
        sys.exit(1)


async def shutdown():
    """
    关闭清理
    """
    logger.info("Shutting down Quant Strategy microservice...")

    try:
        # 清理Nacos服务注册
        logger.info("Deregistering from Nacos...")
        await cleanup_nacos()
        logger.info("Nacos deregistration completed")

        logger.info("Quant Strategy microservice shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    创建FastAPI应用
    """
    app = FastAPI(
        title=settings.name,
        description=f"{settings.name} 微服务 - 量化策略引擎，支持实时信号生成与策略管理",
        version=settings.version,
        lifespan=lifespan
    )

    # 添加中间件
    app.middleware("http")(add_cors_headers)
    app.middleware("http")(log_requests)

    # 注册路由
    app.include_router(health_router)
    app.include_router(strategy_router)

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

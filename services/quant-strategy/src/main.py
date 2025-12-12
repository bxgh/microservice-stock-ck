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

from core.looper import InternalLooper
from adapters.stock_data_provider import data_provider

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
internal_looper = InternalLooper()


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


def validate_environment() -> None:
    """验证必要的环境变量"""
    import os
    
    required_vars = {
        'QS_DB_HOST': '数据库主机地址',
        'QS_DB_USER': '数据库用户名',
        'QS_DB_PASSWORD': '数据库密码'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        logger.error("❌ 缺少必要的环境变量:")
        for var in missing_vars:
            logger.error(f"   - {var}")
        logger.error("请在 docker-compose.dev.yml 或 .env 文件中配置这些环境变量")
        sys.exit(1)
    
    logger.info("✅ 环境变量验证通过")


async def startup():
    """
    服务启动初始化
    """
    logger.info(f"Starting {settings.name} v{settings.version}")
    logger.info(f"Configuration: debug={settings.debug}, log_level={settings.log_level}")

    # 验证必要的环境变量
    validate_environment()

    try:
        logger.info("Starting Quant Strategy microservice...")

        # 初始化数据适配器
        await data_provider.initialize()
        logger.info("✅ 数据适配器初始化成功")

        # 启动内部循环任务
        # 示例：每 60 秒打印一次心跳
        async def heartbeat():
            logger.debug("💓 Internal heartbeat check")

        internal_looper.add_loop(heartbeat, 60, "Heartbeat")
        await internal_looper.start()
        logger.info("✅ 内部循环管理器已启动")

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

        # 停止内部循环
        if internal_looper:
            await internal_looper.stop()

        # 关闭数据提供者
        await data_provider.close()

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


# 创建应用实例（供 uvicorn 使用）
app = create_app()


def main():
    """
    主函数（仅用于直接运行，uvicorn 会直接使用 app 实例）
    """
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=settings.access_log
    )


if __name__ == "__main__":
    main()

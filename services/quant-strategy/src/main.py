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
import traceback
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
from database import init_database, close_database

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
    """验证必要的环境变量 (lenient mode)"""
    import os
    
    logger.info("Validating environment configuration...")
    
    # Only warn about missing DB vars, don't fail (SQLite is default)
    db_vars = ['QS_DB_HOST', 'QS_DB_USER', 'QS_DB_PASSWORD']
    missing_db = [var for var in db_vars if not os.getenv(var)]
    
    if missing_db and settings.database_type == 'mysql':
        logger.warning(f"MySQL mode but missing vars: {', '.join(missing_db)}")
        logger.warning("Falling back to SQLite mode")
    
    logger.info("✅ Environment validation passed")


async def startup():
    """
    服务启动初始化
    """
    """启动任务"""
    logger.info(f"Starting {settings.name} v{settings.version}")
    logger.info(f"Configuration: debug={settings.debug}, log_level={settings.log_level}")

    # 验证必要的环境变量
    validate_environment()

    try:
        logger.info("Starting Quant Strategy microservice...")

        # 1. Initialize database
        logger.info("Initializing database...")
        await init_database()
        logger.info("✅ Database initialized")

        # 2. Initialize data provider
        logger.info("Initializing data provider...")
        await data_provider.initialize()
        logger.info("✅ Data provider initialized")

        # 3. Start internal background tasks
        logger.info("Starting internal looper...")
        # 示例：每 60 秒打印一次心跳
        async def heartbeat():
            logger.debug("💓 Internal heartbeat check")
        internal_looper.add_loop(heartbeat, 60, "Heartbeat")
        await internal_looper.start()
        logger.info("✅ Internal looper started")

        # 4. Register to Nacos
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
        logger.error(f"❌ Startup failed: {e}")
        logger.error(traceback.format_exc())
        logger.warning("⚠️ Service starting in degraded mode")
        # Don't exit - allow service to start in degraded mode
        # sys.exit(1)  # Commented out to allow graceful degradation


async def shutdown():
    """关闭任务"""
    logger.info("Shutting down Quant Strategy microservice...")
    
    try:
        # 1. Stop internal looper
        logger.info("Stopping internal looper...")
        if internal_looper:
            await internal_looper.stop()
        
        # 2. Cleanup Nacos registration
        logger.info("Deregistering from Nacos...")
        await cleanup_nacos()
        
        # 3. Close data provider
        logger.info("Closing data provider...")
        await data_provider.close()
        
        # 4. Close database connections
        logger.info("Closing database...")
        await close_database()
        
        logger.info("✅ Quant Strategy microservice shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")
        logger.error(traceback.format_exc())


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

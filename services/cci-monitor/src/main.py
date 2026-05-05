import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config.settings import settings
from .core.logger import setup_logger
from .core.database import init_db
from .api.health_routes import health_router

from .registry.nacos_registry import register_to_nacos, cleanup_nacos

# 设置日志
logger = setup_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    logger.info(f"Starting {settings.NAME} v{settings.VERSION}...")
    
    # 初始化数据库
    await init_db()
    
    # 注册到 Nacos
    await register_to_nacos()
    
    yield
    
    # 清理 Nacos
    await cleanup_nacos()
    logger.info(f"Shutting down {settings.NAME}...")

def create_app() -> FastAPI:
    """
    创建 FastAPI 应用
    """
    app = FastAPI(
        title=settings.NAME,
        version=settings.VERSION,
        description="Critical Slowing Down (CSD) Market Monitoring System",
        lifespan=lifespan
    )
    
    # 跨域配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(health_router)
    
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

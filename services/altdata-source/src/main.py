from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.health import router as health_router
from src.api.trigger import router as trigger_router
from src.core.config import settings, logger

from src.storage.clickhouse import ClickHouseDAO

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理。
    启动时：初始化连接池、注册 Nacos 等
    关闭时：释放资源
    """
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    # TODO: 后续这里将增加 Nacos 注册逻辑
    
    # 初始化数据库
    try:
        ch_dao = ClickHouseDAO()
        ch_dao.init_database_and_tables()
        # 挂载到 app state 供后续路由使用
        app.state.ch_dao = ch_dao
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse tables: {e}")
        # 根据业务需求，通常底层数据源崩了应该抛出以阻止应用假死
        
    yield
    
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    # TODO: 后续这里将增加资源释放逻辑

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, prefix="/api/v1")
app.include_router(trigger_router, prefix="/api/v1/altdata")

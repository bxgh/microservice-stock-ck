from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from ..config.settings import settings
from .logger import cci_logger

from urllib.parse import quote_plus

# 数据库连接 URL
# 必须对密码进行 URL 编码，防止特殊字符（如 @）破坏连接字符串
encoded_user = quote_plus(settings.DB_USER)
encoded_password = quote_plus(settings.DB_PASSWORD)

DATABASE_URL = (
    f"mysql+aiomysql://{encoded_user}:{encoded_password}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    "?charset=utf8mb4"
)

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=False,
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ORM 基类
class Base(DeclarativeBase):
    pass

async def init_db():
    """
    初始化数据库（开发环境使用，生产环境推荐使用 Alembic）
    """
    try:
        async with engine.begin() as conn:
            # 这里可以根据需要决定是否要自动创建表
            # await conn.run_sync(Base.metadata.create_all)
            pass
        cci_logger.info(f"✓ MySQL Database initialized: {settings.DB_HOST}:{settings.DB_PORT}")
    except Exception as e:
        cci_logger.error(f"✗ Database initialization failed: {e}")
        raise

async def get_db():
    """
    获取数据库会话的依赖项
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

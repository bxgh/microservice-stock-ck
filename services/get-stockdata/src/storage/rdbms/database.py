from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

class AsyncDatabase:
    """异步数据库管理器"""
    
    def __init__(self):
        self._engine = None
        self._session_maker = None
        
    def initialize(self):
        """初始化数据库连接"""
        if self._engine:
            return

        logger.info(f"Connecting to database: {settings.db_host}:{settings.db_port}/{settings.db_name}")
        
        self._engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=settings.connection_pool_size,
            max_overflow=10,
            pool_recycle=3600,
        )
        
        self._session_maker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        logger.info("Database initialized successfully")

    async def close(self):
        """关闭数据库连接"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            logger.info("Database connection closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话 (Context Manager)"""
        if not self._session_maker:
            self.initialize()
            
        session: AsyncSession = self._session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI Dependency"""
        if not self._session_maker:
            self.initialize()
            
        async with self.session() as session:
            yield session

    async def create_tables(self):
        """创建所有表 (仅用于开发环境/简单的初始化)"""
        if not self._engine:
            self.initialize()
            
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

# 全局数据库实例
db = AsyncDatabase()

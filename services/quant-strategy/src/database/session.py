"""
Database session management for Quant Strategy Service

Provides async SQLAlchemy engine and session factory.
"""
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from config.settings import settings
from database.models import Base

logger = logging.getLogger(__name__)

# Global engine instance
_engine = None
_session_factory = None


def get_database_url() -> str:
    """
    Get database connection URL based on settings
    
    Returns:
        Database connection string
    """
    db_type = settings.database_type
    
    if db_type == "mysql":
        # MySQL async connection (requires aiomysql or asyncmy)
        from urllib.parse import quote_plus
        
        # Assuming settings has these MySQL config attributes
        # (You may need to add them to settings.py)
        host = getattr(settings, 'db_host', 'localhost')
        port = getattr(settings, 'db_port', 3306)
        user = getattr(settings, 'db_user', 'root')
        password = getattr(settings, 'db_password', '')
        database = getattr(settings, 'db_name', 'quant_strategy')
        
        encoded_user = quote_plus(user)
        encoded_password = quote_plus(password)
        
        return f"mysql+aiomysql://{encoded_user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
    
    else:
        # Default to SQLite (async)
        return f"sqlite+aiosqlite:///{settings.database_path}"


async def init_database() -> None:
    """
    Initialize database engine and create tables if they don't exist
    """
    global _engine, _session_factory
    
    if _engine is not None:
        logger.warning("Database already initialized")
        return
    
    database_url = get_database_url()
    logger.info(f"Initializing database: {database_url.split('://')[0]}://...")
    
    try:
        # Create async engine with conditional parameters
        engine_kwargs = {
            'echo': False,
            'poolclass': NullPool if 'sqlite' in database_url else None,
            'pool_pre_ping': True
        }
        
        # Only add pool_size for non-SQLite databases
        if 'sqlite' not in database_url:
            engine_kwargs['pool_size'] = settings.connection_pool_size if hasattr(settings, 'connection_pool_size') else 5
        
        _engine = create_async_engine(database_url, **engine_kwargs)
        
        # Create session factory
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


async def close_database() -> None:
    """Close database connections"""
    global _engine, _session_factory
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session (async context manager)
    
    Usage:
        async with get_session() as session:
            result = await session.execute(...)
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Convenience function for direct session creation
def create_session() -> AsyncSession:
    """
    Create a new session (must be closed manually)
    
    Returns:
        AsyncSession instance
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    
    return _session_factory()

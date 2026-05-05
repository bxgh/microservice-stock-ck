"""
MySQL连接池管理器
"""
import logging
import os
from typing import Optional
import aiomysql
import asyncio

logger = logging.getLogger(__name__)


class MySQLPoolManager:
    """MySQL连接池单例管理器"""
    
    _pool: Optional[aiomysql.Pool] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_pool(cls) -> aiomysql.Pool:
        """
        获取MySQL连接池（单例模式）
        
        Returns:
            aiomysql.Pool: MySQL连接池实例
        """
        if cls._pool is None:
            async with cls._lock:
                if cls._pool is None:
                    try:
                        from config.settings import settings
                        cls._pool = await aiomysql.create_pool(
                            host=settings.db_host,
                            port=settings.db_port,
                            user=settings.db_user,
                            password=settings.db_password,
                            db=settings.db_name,
                            charset='utf8mb4',
                            minsize=1,
                            maxsize=settings.connection_pool_size,
                            autocommit=True,
                            connect_timeout=settings.db_connect_timeout
                        )
                        logger.info(f"✓ MySQL连接池已创建: {settings.db_host}:{settings.db_port}")
                    except Exception as e:
                        logger.error(f"创建MySQL连接池失败: {e}")
                        raise
        return cls._pool
    
    @classmethod
    async def close_pool(cls):
        """关闭MySQL连接池"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("MySQL连接池已关闭")

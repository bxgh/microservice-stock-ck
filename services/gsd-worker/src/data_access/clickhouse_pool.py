"""
ClickHouse连接池管理器
"""
import logging
import os
from typing import Optional
import asynch
import asyncio
from config.settings import settings

logger = logging.getLogger(__name__)


class ClickHousePoolManager:
    """ClickHouse连接池单例管理器"""
    
    _pool: Optional[asynch.cursors.DictCursor] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_pool(cls) -> asynch.cursors.DictCursor:
        """
        获取ClickHouse连接池（单例模式）
        """
        if cls._pool is None:
            async with cls._lock:
                if cls._pool is None:
                    try:
                        cls._pool = await asyncio.wait_for(
                            asynch.create_pool(
                                host=os.getenv('CLICKHOUSE_HOST', '127.0.0.1'),
                                port=int(os.getenv('CLICKHOUSE_PORT', 9000)),
                                user=os.getenv('CLICKHOUSE_USER', 'default'),
                                password=os.getenv('CLICKHOUSE_PASSWORD', ''),
                                database=os.getenv('CLICKHOUSE_DB', 'stock_data'),
                                minsize=1,
                                maxsize=10,
                                connect_timeout=settings.db_connect_timeout,
                                send_receive_timeout=settings.db_io_timeout,
                                sync_request_timeout=settings.db_io_timeout
                            ),
                            timeout=settings.db_connect_timeout + settings.db_connect_timeout_buffer
                        )
                        logger.info(f"✓ ClickHouse连接池已创建: {os.getenv('CLICKHOUSE_HOST')}:{os.getenv('CLICKHOUSE_PORT')}")
                    except Exception as e:
                        logger.error(f"创建ClickHouse连接池失败: {e}")
                        raise
        return cls._pool
    
    @classmethod
    async def close_pool(cls):
        """关闭ClickHouse连接池"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("ClickHouse连接池已关闭")

import logging
import os
import asyncio
from typing import Optional
from clickhouse_driver import Client

logger = logging.getLogger(__name__)

class ClickHouseClient:
    """
    ClickHouse Client Wrapper for gsd-worker.
    Provides a consistent interface for async initialization and sync execution.
    """
    
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, 
                 user: Optional[str] = None, password: Optional[str] = None, 
                 database: Optional[str] = None):
        self.host = host or os.getenv('CLICKHOUSE_HOST', '127.0.0.1')
        self.port = port or int(os.getenv('CLICKHOUSE_PORT', 9000))
        self.user = user or os.getenv('CLICKHOUSE_USER', 'default')
        self.password = password or os.getenv('CLICKHOUSE_PASSWORD', '')
        self.database = database or os.getenv('CLICKHOUSE_DB', 'stock_data')
        
        self.client: Optional[Client] = None

    async def connect(self):
        """
        Initialization 'connect' (async for compatibility with service lifecycle)
        """
        try:
            # clickhouse-driver's Client is lazy but we can test it with a simple query
            self.client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                settings={'use_numpy': False}
            )
            # Test connection
            self.client.execute("SELECT 1")
            logger.info(f"✅ ClickHouseClient connected to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"❌ ClickHouseClient connection failed: {e}")
            raise

    def disconnect(self):
        """
        Close connection
        """
        if self.client:
            # clickhouse-driver Client doesn't have an explicit close for the instance, 
            # but it manages connections in a pool. We just null it out.
            self.client = None
            logger.info("✅ ClickHouseClient disconnected")

    def execute(self, query: str, params: Optional[dict] = None):
        """
        Sync execution wrapper
        """
        if not self.client:
            raise RuntimeError("ClickHouseClient not connected. Call connect() first.")
        return self.client.execute(query, params)

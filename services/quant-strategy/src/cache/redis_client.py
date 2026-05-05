"""
Redis Client for Quant Strategy Service

Provides connection pooling and helper methods for caching.
"""
import logging

import redis.asyncio as redis

from config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client with connection pooling
    """

    def __init__(self):
        self.url = settings.redis_url
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None
        self._binary_client: redis.Redis | None = None
        logger.info(f"RedisClient initialized with URL: {self.url}")

    async def initialize(self) -> None:
        """Initialize Redis connection pool"""
        if not self._pool:
            self._pool = redis.ConnectionPool.from_url(
                self.url,
                max_connections=settings.redis_max_connections,
                decode_responses=True
            )
            self._client = redis.Redis(connection_pool=self._pool)

            # Create a separate client for binary data using the same pool?
            # redis-py's ConnectionPool stores connections with a specific encoding/decode_responses.
            # Using the same pool might be problematic if we want different decode settings.
            # However, initializing with separate pool is safer.
            self._binary_pool = redis.ConnectionPool.from_url(
                self.url,
                max_connections=settings.redis_max_connections,
                decode_responses=False
            )
            self._binary_client = redis.Redis(connection_pool=self._binary_pool)

            logger.info("Redis connection pools (String & Binary) created")

            # Test connection
            try:
                await self._client.ping()
                logger.info("✅ Redis connection verified")
            except Exception as e:
                logger.error(f"❌ Redis connection failed: {e}")
                raise

    async def close(self) -> None:
        """Close Redis connection pools"""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

        if self._binary_client:
            await self._binary_client.close()
            self._binary_client = None
        if hasattr(self, '_binary_pool') and self._binary_pool:
            await self._binary_pool.disconnect()
            self._binary_pool = None

        logger.info("Redis connection pools closed")

    async def get_binary_client(self) -> redis.Redis:
        """Get binary-safe client"""
        if not self._binary_client:
            await self.initialize()
        return self._binary_client

    async def get_client(self) -> redis.Redis:
        """Get standard string client"""
        if not self._client:
            await self.initialize()
        return self._client

    async def get(self, key: str) -> str | None:
        """
        Get value by key

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._client:
            await self.initialize()

        try:
            value = await self._client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None
    ) -> bool:
        """
        Set key-value pair with optional TTL

        Args:
            key: Cache key
            value: Value to cache (must be string)
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        if not self._client:
            await self.initialize()

        try:
            if ttl:
                await self._client.setex(key, ttl, value)
            else:
                await self._client.set(key, value)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key to delete

        Returns:
            True if deleted
        """
        if not self._client:
            await self.initialize()

        try:
            result = await self._client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._client:
            await self.initialize()

        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False


# Cache key schema design
class CacheKeys:
    """Centralized cache key definitions"""

    @staticmethod
    def quote(stock_code: str) -> str:
        """Real-time quote cache key"""
        return f"quant:quote:{stock_code}"

    @staticmethod
    def stock_info(stock_code: str) -> str:
        """Stock basic info cache key"""
        return f"quant:stock_info:{stock_code}"

    @staticmethod
    def history(stock_code: str, period: str, interval: str) -> str:
        """Historical K-line cache key"""
        return f"quant:history:{stock_code}:{period}:{interval}"


# Cache TTL configuration (in seconds)
class CacheTTL:
    """TTL settings for different data types"""
    QUOTE = 5          # Real-time quotes: 5 seconds
    STOCK_INFO = 86400 * 7  # Stock info: 7 days
    HISTORY = 86400    # Historical data: 1 day


# Global singleton
redis_client = RedisClient()

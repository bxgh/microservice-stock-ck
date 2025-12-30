
import os
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

class RedisPoolManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RedisPoolManager()
        return cls._instance
        
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # Support separate host/port envs if URL not provided or if we want to build it
        if not os.getenv("REDIS_URL"):
            host = os.getenv("REDIS_HOST", "localhost")
            port = os.getenv("REDIS_PORT", "6379")
            db = os.getenv("REDIS_DB", "0")
            password = os.getenv("REDIS_PASSWORD", None)
            auth_part = f":{password}@" if password else ""
            self.redis_url = f"redis://{auth_part}{host}:{port}/{db}"

        self.pool = None

    async def get_redis(self) -> redis.Redis:
        if self.pool is None:
             self.pool = redis.from_url(
                self.redis_url, 
                encoding="utf-8", 
                decode_responses=True,
                max_connections=10
            )
             logger.info(f"Redis connection pool created: {self.redis_url}")
        return self.pool

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Redis connection pool closed")

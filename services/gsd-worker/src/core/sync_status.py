
import logging
from datetime import datetime
import pytz
from typing import Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class SyncStatusTracker:
    """
    分笔同步状态跟踪器 (Redis)
    """
    
    REDIS_STATUS_EXPIRE_SECONDS = 86400 * 7  # 7天

    def __init__(self, redis_client: Optional[redis.Redis]):
        self.redis = redis_client

    async def update(
        self, 
        stock_code: str, 
        trade_date: str, 
        status: str, 
        count: int = 0,
        start_t: str = "",
        end_t: str = "",
        error: str = ""
    ) -> None:
        """更新 Redis 中的采集状态"""
        if not self.redis:
            return
        
        key = f"tick_sync:status:{trade_date}"
        sync_time = datetime.now(CST).isoformat()
        # 格式: {status}|{tick_count}|{data_start}|{data_end}|{sync_time}|{error}
        value = f"{status}|{count}|{start_t}|{end_t}|{sync_time}|{error}"
        
        try:
            await self.redis.hset(key, stock_code, value)
            # 设置过期时间
            await self.redis.expire(key, self.REDIS_STATUS_EXPIRE_SECONDS)
        except Exception as e:
            logger.warning(f"Failed to update sync status in Redis: {e}")

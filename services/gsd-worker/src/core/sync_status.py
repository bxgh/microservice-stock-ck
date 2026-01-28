import logging
from typing import Optional
import redis.asyncio as redis
from gsd_shared.tick.status import SyncStatusTracker as SharedTracker

logger = logging.getLogger(__name__)

class SyncStatusTracker(SharedTracker):
    """
    分笔同步状态跟踪器 (Refactored to use gsd_shared)
    Maintains compatibility with existing gsd-worker calls while leveraging shared logic.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis]):
        super().__init__(redis_client)

    async def update(self, *args, **kwargs):
        """Legacy alias for update_status"""
        return await self.update_status(*args, **kwargs)

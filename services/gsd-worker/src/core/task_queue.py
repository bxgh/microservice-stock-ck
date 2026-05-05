
import os
import logging
import redis.asyncio as redis
from typing import List, Optional

logger = logging.getLogger(__name__)

class TickTaskQueue:
    """
    分布式任务队列管理 (Redis)
    负责任务的推送、消费、确认及断点续传
    """
    QUEUE_NAME = "{gsd:tick}:tasks"
    PROCESSING_PREFIX = "{gsd:tick}:processing"
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        if not self.redis:
            logger.warning("TickTaskQueue initialized without Redis client")

    async def push(self, stock_codes: List[str]) -> int:
        """[Producer] 将股票代码推入 Redis 任务队列"""
        if not self.redis:
            raise RuntimeError("Redis 客户端未初始化")
            
        try:
            # 清空旧队列
            await self.redis.delete(self.QUEUE_NAME)
            
            # 批量推送
            if stock_codes:
                await self.redis.lpush(self.QUEUE_NAME, *stock_codes)
                logger.info(f"📤 已向 Redis 队列 {self.QUEUE_NAME} 推送 {len(stock_codes)} 个任务")
                return len(stock_codes)
            return 0
        except Exception as e:
            logger.error(f"❌ 推送 Redis 任务失败: {e}")
            raise

    async def consume(self, node_id: Optional[str] = None) -> Optional[str]:
        """[Consumer] 从 Redis 队列获取一个新任务"""
        if not self.redis:
            return None
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{self.PROCESSING_PREFIX}:{node_id}"
        
        try:
            # 直接获取新任务
            task = await self.redis.brpoplpush(self.QUEUE_NAME, processing_queue, timeout=5)
            # redis-py's brpoplpush returns None if timeout, or string/bytes if found.
            # decode_responses=True in client ensures string.
            return task
        except Exception as e:
            logger.error(f"❌ 获取 Redis 任务失败: {e}")
            return None

    async def ack(self, stock_code: str, node_id: Optional[str] = None) -> bool:
        """[Consumer] 任务完成确认，从处理中队列移除"""
        if not self.redis:
            return False
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{self.PROCESSING_PREFIX}:{node_id}"
        
        try:
            # LREM distinct count value
            await self.redis.lrem(processing_queue, 1, stock_code)
            return True
        except Exception as e:
            logger.error(f"❌ 确认 Redis 任务失败 ({stock_code}): {e}")
            return False

    async def recover(self, node_id: Optional[str] = None) -> List[str]:
        """[Consumer] 启动时恢复上次意外中断的任务"""
        if not self.redis:
            return []
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{self.PROCESSING_PREFIX}:{node_id}"
        
        try:
            # 获取所有处理中任务
            tasks = await self.redis.lrange(processing_queue, 0, -1)
            if tasks:
                logger.info(f"♻️ 发现 {len(tasks)} 个未完成任务，准备恢复")
            return tasks
        except Exception as e:
            logger.error(f"❌ 恢复 Redis 任务失败: {e}")
            return []

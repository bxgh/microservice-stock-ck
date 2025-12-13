"""事件总线

简单的内存事件总线，用于应用内部组件解耦。
支持发布/订阅模式。
"""

import asyncio
import logging
from typing import Callable, Any, Awaitable, Union

logger = logging.getLogger(__name__)

# 类型定义：处理器可以是同步函数或异步协程
EventHandler = Union[Callable[[Any], Any], Callable[[Any], Awaitable[Any]]]

class EventBus:
    """事件总线 (单例)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance
    
    def __init__(self):
        pass

    def subscribe(self, topic: str, handler: EventHandler):
        """订阅主题"""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str, handler: EventHandler):
        """取消订阅"""
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(handler)
                logger.debug(f"Unsubscribed from topic: {topic}")
            except ValueError:
                pass

    async def publish(self, topic: str, event: Any):
        """发布事件"""
        if topic not in self._subscribers:
            return
            
        handlers = self._subscribers[topic]
        logger.debug(f"Publishing event to {topic} ({len(handlers)} handlers)")
        
        # 并发执行所有处理器
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(asyncio.create_task(self._safe_execute(handler, event)))
            else:
                # 同步处理器也在 Task 中运行以免阻塞 Loop
                tasks.append(asyncio.create_task(self._safe_execute_sync(handler, event)))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_execute(self, handler, event):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    async def _safe_execute_sync(self, handler, event):
        try:
            handler(event)
        except Exception as e:
            logger.error(f"Error handling event (sync): {e}", exc_info=True)

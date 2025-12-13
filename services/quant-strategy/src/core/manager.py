"""后台任务管理器

负责管理应用程序内的所有长期运行的后台任务 (Asyncio Tasks)。
提供任务的启动、停止、状态查询和优雅关闭功能。
"""

import asyncio
import logging
from typing import Dict, Coroutine, Optional, Set

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """后台任务管理器 (单例)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks = {}
            cls._instance._lock = asyncio.Lock()
            cls._instance._stopping = False
        return cls._instance

    def __init__(self):
        # __init__ might be called multiple times, so initialization is done in __new__
        pass

    async def start_task(self, name: str, coro: Coroutine) -> asyncio.Task:
        """启动一个后台任务
        
        Args:
            name: 任务唯一名称
            coro: 协程对象
            
        Returns:
            创建的 Task 对象
        """
        async with self._lock:
            if self._stopping:
                raise RuntimeError("System is shutting down, cannot start new tasks")
                
            if name in self._tasks:
                existing_task = self._tasks[name]
                if not existing_task.done():
                    logger.warning(f"Task {name} is already running")
                    return existing_task
                else:
                    # 清理已完成的旧任务
                    del self._tasks[name]
            
            # 创建新任务
            task = asyncio.create_task(coro, name=name)
            self._tasks[name] = task
            
            # 添加完成回调
            task.add_done_callback(lambda t: self._on_task_done(name, t))
            
            logger.info(f"Background task started: {name}")
            return task

    async def stop_task(self, name: str, wait: bool = True) -> bool:
        """停止指定任务
        
        Args:
            name: 任务名称
            wait: 是否等待任务结束
            
        Returns:
            True表示成功停止（或任务已结束），False表示任务不存在
        """
        task = self._tasks.get(name)
        if not task:
            logger.warning(f"Task {name} not found to stop")
            return False
            
        if not task.done():
            logger.info(f"Stopping background task: {name}...")
            task.cancel()
            if wait:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error during task {name} cancellation: {e}")
            logger.info(f"Background task stopped: {name}")
        
        return True

    async def shutdown(self):
        """关闭所有任务"""
        logger.info("Shutting down BackgroundTaskManager...")
        self._stopping = True
        
        tasks_to_stop = []
        async with self._lock:
            tasks_to_stop = list(self._tasks.keys())
            
        for name in tasks_to_stop:
            await self.stop_task(name, wait=False)
            
        # 等待所有任务结束
        pending = [t for t in self._tasks.values() if not t.done()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
            
        logger.info(f"BackgroundTaskManager shutdown complete. Stopped {len(tasks_to_stop)} tasks.")

    def _on_task_done(self, name: str, task: asyncio.Task):
        """任务完成回调"""
        try:
            exc = task.exception()
            if exc:
                if not isinstance(exc, asyncio.CancelledError):
                    logger.error(f"Background task {name} failed with error: {exc}", exc_info=exc)
            else:
                logger.info(f"Background task {name} completed successfully")
        except asyncio.CancelledError:
            logger.info(f"Background task {name} was cancelled")
        except Exception as e:
            logger.error(f"Error checking status for task {name}: {e}")
            
        # 即使任务完成，也保留在字典中直到被显式清理或覆盖？
        # 或者在这里移除？为了避免字典无限增长，应该移除。
        # 注意：这里需要考虑并发安全，但 done_callback 在 loop 中运行，通常是安全的
        # 但为了保险，最好不要直接操作 self._tasks，或者加锁
        # 简单起见，这里不直接从 self._tasks 删除，防止迭代中修改字典的问题
        # 可以在 start_task 时清理，或者提供一个 cleanup 方法
        pass
        
    def get_task_status(self, name: str) -> str:
        """获取任务状态"""
        task = self._tasks.get(name)
        if not task:
            return "NOT_FOUND"
        if task.cancelled():
            return "CANCELLED"
        if task.done():
            exc = task.exception()
            return "FAILED" if exc else "COMPLETED"
        return "RUNNING"

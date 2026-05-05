import asyncio
import logging
import traceback
from collections.abc import Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class InternalLooper:
    """
    内部后台任务循环管理器

    用于处理服务内部的高频、轻量级维护任务，例如：
    - 刷新本地缓存
    - 发送心跳
    - 清理临时文件

    不处理复杂的业务调度，业务调度由外部 task-scheduler 通过 API 触发。
    """

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task] = []
        self._running: bool = False
        self._loops: list[dict] = []

    def add_loop(self, func: Callable, interval_seconds: int, name: str | None = None) -> None:
        """
        添加一个循环任务

        Args:
            func: 异步执行函数
            interval_seconds: 执行间隔(秒)
            name: 任务名称
        """
        self._loops.append({
            "func": func,
            "interval": interval_seconds,
            "name": name or func.__name__
        })

    async def start(self) -> None:
        """启动所有后台循环"""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting InternalLooper with {len(self._loops)} loops")

        for loop_config in self._loops:
            task = asyncio.create_task(
                self._run_loop(
                    loop_config["func"],
                    loop_config["interval"],
                    loop_config["name"]
                )
            )
            self._tasks.append(task)

    async def stop(self) -> None:
        """停止所有任务"""
        self._running = False
        logger.info("Stopping InternalLooper...")

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

        logger.info("InternalLooper stopped")

    async def _run_loop(self, func: Callable, interval: int, name: str) -> None:
        """单个任务的执行循环"""
        logger.info(f"Started loop task: {name} (interval={interval}s)")

        while self._running:
            try:
                start_time = datetime.now()
                await func()

                # 计算需要休眠的时间，保持精确间隔
                elapsed = (datetime.now() - start_time).total_seconds()
                sleep_time = max(0.1, interval - elapsed)

                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in loop task {name}: {e}")
                logger.error(traceback.format_exc())
                # 出错后短暂暂停避免死循环
                await asyncio.sleep(5)

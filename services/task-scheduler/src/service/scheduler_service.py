"""
调度器服务
"""

import logging
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

logger = logging.getLogger(__name__)


class SchedulerService:
    """调度器服务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._setup_scheduler()

    def _setup_scheduler(self):
        """设置调度器"""
        jobstores = {
            'default': MemoryJobStore()
        }

        executors = {
            'default': AsyncIOExecutor()
        }

        job_defaults = {
            'coalesce': True,
            'max_instances': 3,
            'misfire_grace_time': 30
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.config.get("timezone", "Asia/Shanghai")
        )

    async def start(self):
        """启动调度器"""
        if self.scheduler:
            self.scheduler.start()
            logger.info("Scheduler started")

    async def shutdown(self, wait=True):
        """关闭调度器"""
        if self.scheduler:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")

    def get_scheduler(self) -> AsyncIOScheduler:
        """获取调度器实例"""
        return self.scheduler

    def add_job(self, func, trigger, args=None, kwargs=None, **trigger_args):
        """添加任务"""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")

        return self.scheduler.add_job(
            func,
            trigger,
            args=args or [],
            kwargs=kwargs or {},
            **trigger_args
        )

    def remove_job(self, job_id: str):
        """移除任务"""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")

        try:
            self.scheduler.remove_job(job_id)
            return True
        except:
            return False

    def pause_job(self, job_id: str):
        """暂停任务"""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")

        try:
            self.scheduler.pause_job(job_id)
            return True
        except:
            return False

    def resume_job(self, job_id: str):
        """恢复任务"""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")

        try:
            self.scheduler.resume_job(job_id)
            return True
        except:
            return False

    def get_jobs(self):
        """获取所有任务"""
        if not self.scheduler:
            return []

        return self.scheduler.get_jobs()

    def get_job(self, job_id: str):
        """获取指定任务"""
        if not self.scheduler:
            return None

        return self.scheduler.get_job(job_id)
"""
任务服务 - 简化版任务管理业务逻辑
"""

import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class TaskService:
    """简化版任务服务类"""

    def __init__(self, scheduler_service=None, execution_service=None, config: Dict[str, Any] = None):
        self.scheduler_service = scheduler_service
        self.execution_service = execution_service
        self.config = config or {}

        # 内存存储任务数据
        self.tasks = {}
        self.task_executions = {}

    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务"""
        try:
            task_id = str(uuid.uuid4())

            # 验证必要字段
            if not task_data.get('name'):
                raise ValueError("Task name is required")

            # 构建任务对象
            task = {
                'task_id': task_id,
                'name': task_data.get('name'),
                'description': task_data.get('description', ''),
                'task_type': task_data.get('task_type', 'http'),
                'config': task_data.get('config', {}),
                'schedule': task_data.get('schedule', {}),
                'enabled': task_data.get('enabled', True),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'status': 'created',
                'last_run': None,
                'next_run': None
            }

            # 保存任务
            self.tasks[task_id] = task

            # 如果启用，添加到调度器
            if task['enabled'] and self.scheduler_service:
                await self._schedule_task(task)

            logger.info(f"Task created: {task_id}")
            return task

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        return self.tasks.get(task_id)

    async def list_tasks(self, limit: int = 100, offset: int = 0, status: str = None) -> List[Dict[str, Any]]:
        """获取任务列表"""
        tasks = list(self.tasks.values())

        # 过滤状态
        if status:
            tasks = [t for t in tasks if t.get('status') == status]

        # 排序
        tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # 分页
        return tasks[offset:offset + limit]

    async def update_task(self, task_id: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新任务"""
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]

        # 更新字段
        updatable_fields = ['name', 'description', 'task_type', 'config', 'schedule', 'enabled']
        for field in updatable_fields:
            if field in task_data:
                task[field] = task_data[field]

        task['updated_at'] = datetime.now().isoformat()

        # 重新调度
        if self.scheduler_service:
            await self._reschedule_task(task)

        logger.info(f"Task updated: {task_id}")
        return task

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id not in self.tasks:
            return False

        # 从调度器中移除
        if self.scheduler_service:
            scheduler = self.scheduler_service.get_scheduler()
            if scheduler:
                try:
                    scheduler.remove_job(task_id)
                except:
                    pass

        # 删除任务
        del self.tasks[task_id]

        # 删除执行记录
        if task_id in self.task_executions:
            del self.task_executions[task_id]

        logger.info(f"Task deleted: {task_id}")
        return True

    async def start_task(self, task_id: str) -> bool:
        """启动任务"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task['enabled'] = True
        task['status'] = 'running'
        task['updated_at'] = datetime.now().isoformat()

        # 添加到调度器
        if self.scheduler_service:
            await self._schedule_task(task)

        logger.info(f"Task started: {task_id}")
        return True

    async def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task['enabled'] = False
        task['status'] = 'stopped'
        task['updated_at'] = datetime.now().isoformat()

        # 从调度器中移除
        if self.scheduler_service:
            scheduler = self.scheduler_service.get_scheduler()
            if scheduler:
                try:
                    scheduler.pause_job(task_id)
                except:
                    pass

        logger.info(f"Task stopped: {task_id}")
        return True

    async def get_stats(self) -> Dict[str, Any]:
        """获取任务统计"""
        total_tasks = len(self.tasks)
        running_tasks = len([t for t in self.tasks.values() if t.get('status') == 'running'])
        stopped_tasks = len([t for t in self.tasks.values() if t.get('status') == 'stopped'])
        created_tasks = len([t for t in self.tasks.values() if t.get('status') == 'created'])

        return {
            'total': total_tasks,
            'running': running_tasks,
            'stopped': stopped_tasks,
            'created': created_tasks,
            'completed': 0,  # 简化版暂不支持
            'failed': 0       # 简化版暂不支持
        }

    async def _schedule_task(self, task: Dict[str, Any]):
        """调度任务"""
        if not self.scheduler_service:
            return

        scheduler = self.scheduler_service.get_scheduler()
        if not scheduler:
            return

        try:
            from apscheduler.triggers.interval import IntervalTrigger
            from apscheduler.triggers.cron import CronTrigger

            # 解析调度配置
            schedule = task.get('schedule', {})

            if schedule.get('type') == 'interval':
                # 间隔调度
                seconds = schedule.get('seconds', 60)
                scheduler.add_job(
                    self._execute_task,
                    IntervalTrigger(seconds=seconds),
                    id=task['task_id'],
                    args=[task]
                )
            elif schedule.get('type') == 'cron':
                # Cron调度
                cron_expr = schedule.get('expression', '0 * * * *')
                scheduler.add_job(
                    self._execute_task,
                    CronTrigger.from_crontab(cron_expr),
                    id=task['task_id'],
                    args=[task]
                )
            else:
                # 默认间隔调度
                scheduler.add_job(
                    self._execute_task,
                    IntervalTrigger(seconds=60),
                    id=task['task_id'],
                    args=[task]
                )

            task['status'] = 'running'
            logger.info(f"Task scheduled: {task['task_id']}")

        except Exception as e:
            logger.error(f"Failed to schedule task {task['task_id']}: {e}")

    async def _reschedule_task(self, task: Dict[str, Any]):
        """重新调度任务"""
        if not self.scheduler_service:
            return

        scheduler = self.scheduler_service.get_scheduler()
        if not scheduler:
            return

        try:
            # 先移除现有任务
            scheduler.remove_job(task['task_id'])
        except:
            pass

        # 如果任务启用，重新调度
        if task['enabled']:
            await self._schedule_task(task)
        else:
            task['status'] = 'stopped'

    async def _execute_task(self, task: Dict[str, Any]):
        """执行任务"""
        task_id = task['task_id']

        try:
            logger.info(f"Executing task: {task_id}")

            # 更新任务状态
            task['last_run'] = datetime.now().isoformat()

            # 执行任务
            if self.execution_service:
                result = await self.execution_service.execute_task({
                    'task_id': task_id,
                    'task_type': task['task_type'],
                    'config': task['config']
                })

                # 记录执行结果
                execution_record = {
                    'task_id': task_id,
                    'executed_at': datetime.now().isoformat(),
                    'result': result,
                    'status': 'success' if result.get('success') else 'failed'
                }

                if task_id not in self.task_executions:
                    self.task_executions[task_id] = []

                self.task_executions[task_id].append(execution_record)

                # 只保留最近10次执行记录
                if len(self.task_executions[task_id]) > 10:
                    self.task_executions[task_id] = self.task_executions[task_id][-10:]

                logger.info(f"Task executed: {task_id}, result: {result.get('success', False)}")

        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {e}")

            # 记录失败记录
            execution_record = {
                'task_id': task_id,
                'executed_at': datetime.now().isoformat(),
                'result': {'success': False, 'error': str(e)},
                'status': 'failed'
            }

            if task_id not in self.task_executions:
                self.task_executions[task_id] = []

            self.task_executions[task_id].append(execution_record)
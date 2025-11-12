"""
任务服务 - 任务管理业务逻辑
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from models.task_models import TaskDefinition, TaskInfo, TaskStatus, ApiResponse
from repository.task_repository import TaskRepository
from plugins.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


class TaskService:
    """任务服务类"""

    def __init__(self, task_repository: TaskRepository, plugin_manager: PluginManager):
        self.task_repository = task_repository
        self.plugin_manager = plugin_manager

    async def create_task(self, definition: TaskDefinition) -> TaskInfo:
        """创建任务"""
        try:
            # 验证任务类型
            if definition.task_type not in self.plugin_manager.get_available_plugins():
                raise ValueError(f"Unknown task type: {definition.task_type}")

            # 验证任务配置
            plugin = self.plugin_manager.get_plugin(definition.task_type)
            if not await plugin.validate_config(definition.config):
                raise ValueError("Invalid task configuration")

            # 生成任务ID
            task_id = str(uuid.uuid4())

            # 保存到数据库
            if not self.task_repository.create_task(task_id, definition):
                raise RuntimeError("Failed to create task in database")

            # 获取创建的任务信息
            task_info = self.task_repository.get_task(task_id)
            if not task_info:
                raise RuntimeError("Failed to retrieve created task")

            logger.info(f"Task created successfully: {task_id}")
            return task_info

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise

    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        try:
            task_info = self.task_repository.get_task(task_id)
            if task_info:
                # 获取最近执行记录
                from repository.execution_repository import ExecutionRepository
                exec_repo = ExecutionRepository()
                last_execution = exec_repo.get_last_execution(task_id)
                task_info.last_execution = last_execution

            return task_info
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    async def list_tasks(self, page: int = 1, page_size: int = 20,
                        status: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> List[TaskInfo]:
        """查询任务列表"""
        try:
            tasks = self.task_repository.list_tasks(page, page_size, status, tags)

            # 为每个任务添加最近执行记录
            from repository.execution_repository import ExecutionRepository
            exec_repo = ExecutionRepository()

            for task in tasks:
                task.last_execution = exec_repo.get_last_execution(task.task_id)

            return tasks
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []

    async def update_task(self, task_id: str, definition: TaskDefinition) -> TaskInfo:
        """更新任务"""
        try:
            # 检查任务是否存在
            existing_task = self.task_repository.get_task(task_id)
            if not existing_task:
                raise ValueError("Task not found")

            # 验证任务类型
            if definition.task_type not in self.plugin_manager.get_available_plugins():
                raise ValueError(f"Unknown task type: {definition.task_type}")

            # 验证任务配置
            plugin = self.plugin_manager.get_plugin(definition.task_type)
            if not await plugin.validate_config(definition.config):
                raise ValueError("Invalid task configuration")

            # 更新数据库
            if not self.task_repository.update_task(task_id, definition):
                raise RuntimeError("Failed to update task in database")

            # 获取更新后的任务信息
            task_info = await self.get_task(task_id)
            if not task_info:
                raise RuntimeError("Failed to retrieve updated task")

            logger.info(f"Task updated successfully: {task_id}")
            return task_info

        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            # 检查任务是否存在
            existing_task = self.task_repository.get_task(task_id)
            if not existing_task:
                raise ValueError("Task not found")

            # 从数据库删除
            success = self.task_repository.delete_task(task_id)
            if success:
                logger.info(f"Task deleted successfully: {task_id}")

            return success
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise

    async def trigger_task(self, task_id: str) -> bool:
        """手动触发任务"""
        try:
            task_info = self.task_repository.get_task(task_id)
            if not task_info:
                raise ValueError("Task not found")

            if not task_info.definition.enabled:
                raise ValueError("Task is disabled")

            # 通过调度服务触发任务
            from .scheduler_service import SchedulerService
            scheduler_service = SchedulerService(self.task_repository)
            return scheduler_service.trigger_task(task_id)

        except Exception as e:
            logger.error(f"Failed to trigger task {task_id}: {e}")
            raise

    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            task_info = self.task_repository.get_task(task_id)
            if not task_info:
                raise ValueError("Task not found")

            # 更新任务状态
            success = self.task_repository.update_task_status(task_id, TaskStatus.PAUSED)
            if success:
                # 暂停调度器中的任务
                from .scheduler_service import SchedulerService
                scheduler_service = SchedulerService(self.task_repository)
                scheduler_service.pause_job(task_id)
                logger.info(f"Task paused successfully: {task_id}")

            return success
        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {e}")
            raise

    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            task_info = self.task_repository.get_task(task_id)
            if not task_info:
                raise ValueError("Task not found")

            # 更新任务状态
            success = self.task_repository.update_task_status(task_id, TaskStatus.PENDING)
            if success:
                # 恢复调度器中的任务
                from .scheduler_service import SchedulerService
                scheduler_service = SchedulerService(self.task_repository)
                scheduler_service.resume_job(task_id)
                logger.info(f"Task resumed successfully: {task_id}")

            return success
        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            raise

    async def get_tasks_by_type(self, task_type: str) -> List[TaskInfo]:
        """根据类型获取任务"""
        try:
            return self.task_repository.get_tasks_by_type(task_type)
        except Exception as e:
            logger.error(f"Failed to get tasks by type {task_type}: {e}")
            return []

    async def get_enabled_tasks(self) -> List[TaskInfo]:
        """获取启用的任务"""
        try:
            return self.task_repository.get_enabled_tasks()
        except Exception as e:
            logger.error(f"Failed to get enabled tasks: {e}")
            return []

    async def validate_task_definition(self, definition: TaskDefinition) -> List[str]:
        """验证任务定义"""
        errors = []

        # 基本验证
        if not definition.name or not definition.name.strip():
            errors.append("Task name is required")

        if not definition.task_type or not definition.task_type.strip():
            errors.append("Task type is required")

        # 验证调度配置
        if not definition.cron_expression and not definition.interval_seconds:
            errors.append("Either cron_expression or interval_seconds is required")

        # 验证插件
        if definition.task_type not in self.plugin_manager.get_available_plugins():
            errors.append(f"Unknown task type: {definition.task_type}")
        else:
            plugin = self.plugin_manager.get_plugin(definition.task_type)
            if not await plugin.validate_config(definition.config):
                errors.append("Invalid task configuration for the plugin")

        return errors

    async def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        try:
            task_info = self.task_repository.get_task(task_id)
            if not task_info:
                raise ValueError("Task not found")

            # 更新任务定义
            definition = task_info.definition
            definition.enabled = True

            success = self.task_repository.update_task(task_id, definition)
            if success:
                # 恢复调度器中的任务
                from .scheduler_service import SchedulerService
                scheduler_service = SchedulerService(self.task_repository)
                scheduler_service.resume_job(task_id)
                logger.info(f"Task enabled successfully: {task_id}")

            return success
        except Exception as e:
            logger.error(f"Failed to enable task {task_id}: {e}")
            raise

    async def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        try:
            task_info = self.task_repository.get_task(task_id)
            if not task_info:
                raise ValueError("Task not found")

            # 更新任务定义
            definition = task_info.definition
            definition.enabled = False

            success = self.task_repository.update_task(task_id, definition)
            if success:
                # 暂停调度器中的任务
                from .scheduler_service import SchedulerService
                scheduler_service = SchedulerService(self.task_repository)
                scheduler_service.pause_job(task_id)
                logger.info(f"Task disabled successfully: {task_id}")

            return success
        except Exception as e:
            logger.error(f"Failed to disable task {task_id}: {e}")
            raise

    def get_task_statistics(self, task_id: str, days: int = 30) -> dict:
        """获取任务统计信息"""
        try:
            from repository.execution_repository import ExecutionRepository
            exec_repo = ExecutionRepository()
            return exec_repo.get_execution_statistics(task_id, days)
        except Exception as e:
            logger.error(f"Failed to get task statistics for {task_id}: {e}")
            return {}
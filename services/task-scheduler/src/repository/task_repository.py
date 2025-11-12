"""
任务数据访问层
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from models.task_models import TaskDefinition, TaskInfo, TaskStatus

logger = logging.getLogger(__name__)


class TaskRepository:
    """任务数据访问对象"""

    def __init__(self, db_path: str = "data/taskscheduler.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    description TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    cron_expression TEXT,
                    interval_seconds INTEGER,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    timeout INTEGER DEFAULT 300,
                    max_retries INTEGER DEFAULT 3,
                    retry_delay INTEGER DEFAULT 60,
                    config TEXT,
                    tags TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    next_run_time TIMESTAMP,
                    execution_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_task(self, task_id: str, definition: TaskDefinition) -> bool:
        """创建任务"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO tasks (
                        task_id, name, task_type, description, enabled,
                        cron_expression, interval_seconds, start_date, end_date,
                        timeout, max_retries, retry_delay, config, tags,
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    definition.name,
                    definition.task_type,
                    definition.description,
                    definition.enabled,
                    definition.cron_expression,
                    definition.interval_seconds,
                    definition.start_date,
                    definition.end_date,
                    definition.timeout,
                    definition.max_retries,
                    definition.retry_delay,
                    json.dumps(definition.config) if definition.config else None,
                    json.dumps(definition.tags) if definition.tags else None,
                    TaskStatus.PENDING,
                    datetime.now(),
                    datetime.now()
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM tasks WHERE task_id = ?
                """, (task_id,))
                row = cursor.fetchone()

                if row:
                    return self._row_to_task_info(row)
        except Exception as e:
            logger.error(f"Failed to get task: {e}")
        return None

    def list_tasks(self, page: int = 1, page_size: int = 20,
                   status: Optional[str] = None, tags: Optional[List[str]] = None) -> List[TaskInfo]:
        """查询任务列表"""
        try:
            with self._get_connection() as conn:
                # 构建查询条件
                where_conditions = []
                params = []

                if status:
                    where_conditions.append("status = ?")
                    params.append(status)

                if tags:
                    for tag in tags:
                        where_conditions.append("tags LIKE ?")
                        params.append(f"%{tag}%")

                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # 查询总数
                count_query = f"SELECT COUNT(*) FROM tasks {where_clause}"
                total = conn.execute(count_query, params).fetchone()[0]

                # 分页查询
                offset = (page - 1) * page_size
                query = f"""
                    SELECT * FROM tasks {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([page_size, offset])

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [self._row_to_task_info(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []

    def update_task(self, task_id: str, definition: TaskDefinition) -> bool:
        """更新任务"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE tasks SET
                        name = ?, task_type = ?, description = ?, enabled = ?,
                        cron_expression = ?, interval_seconds = ?, start_date = ?, end_date = ?,
                        timeout = ?, max_retries = ?, retry_delay = ?, config = ?, tags = ?,
                        updated_at = ?
                    WHERE task_id = ?
                """, (
                    definition.name,
                    definition.task_type,
                    definition.description,
                    definition.enabled,
                    definition.cron_expression,
                    definition.interval_seconds,
                    definition.start_date,
                    definition.end_date,
                    definition.timeout,
                    definition.max_retries,
                    definition.retry_delay,
                    json.dumps(definition.config) if definition.config else None,
                    json.dumps(definition.tags) if definition.tags else None,
                    datetime.now(),
                    task_id
                ))
                conn.commit()
                return conn.total_changes > 0
        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            with self._get_connection() as conn:
                # 删除相关的执行记录
                conn.execute("DELETE FROM executions WHERE task_id = ?", (task_id,))
                # 删除任务
                conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete task: {e}")
            return False

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新任务状态"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE tasks SET status = ?, updated_at = ?
                    WHERE task_id = ?
                """, (status, datetime.now(), task_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return False

    def update_task_statistics(self, task_id: str, execution_success: bool) -> bool:
        """更新任务统计"""
        try:
            with self._get_connection() as conn:
                if execution_success:
                    conn.execute("""
                        UPDATE tasks SET
                            execution_count = execution_count + 1,
                            success_count = success_count + 1,
                            updated_at = ?
                        WHERE task_id = ?
                    """, (datetime.now(), task_id))
                else:
                    conn.execute("""
                        UPDATE tasks SET
                            execution_count = execution_count + 1,
                            failure_count = failure_count + 1,
                            updated_at = ?
                        WHERE task_id = ?
                    """, (datetime.now(), task_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update task statistics: {e}")
            return False

    def update_next_run_time(self, task_id: str, next_run_time: Optional[datetime]) -> bool:
        """更新下次运行时间"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE tasks SET next_run_time = ?
                    WHERE task_id = ?
                """, (next_run_time, task_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update next run time: {e}")
            return False

    def get_tasks_by_type(self, task_type: str) -> List[TaskInfo]:
        """根据类型获取任务"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM tasks WHERE task_type = ? ORDER BY created_at
                """, (task_type,))
                rows = cursor.fetchall()
                return [self._row_to_task_info(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get tasks by type: {e}")
            return []

    def get_enabled_tasks(self) -> List[TaskInfo]:
        """获取启用的任务"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM tasks WHERE enabled = 1 ORDER BY created_at
                """)
                rows = cursor.fetchall()
                return [self._row_to_task_info(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get enabled tasks: {e}")
            return []

    def _row_to_task_info(self, row) -> TaskInfo:
        """将数据库行转换为TaskInfo对象"""
        return TaskInfo(
            task_id=row['task_id'],
            definition=TaskDefinition(
                name=row['name'],
                task_type=row['task_type'],
                description=row['description'],
                enabled=bool(row['enabled']),
                cron_expression=row['cron_expression'],
                interval_seconds=row['interval_seconds'],
                start_date=datetime.fromisoformat(row['start_date']) if row['start_date'] else None,
                end_date=datetime.fromisoformat(row['end_date']) if row['end_date'] else None,
                timeout=row['timeout'],
                max_retries=row['max_retries'],
                retry_delay=row['retry_delay'],
                config=json.loads(row['config']) if row['config'] else {},
                tags=json.loads(row['tags']) if row['tags'] else []
            ),
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            last_execution=None,  # 需要单独查询
            next_run_time=datetime.fromisoformat(row['next_run_time']) if row['next_run_time'] else None,
            execution_count=row['execution_count'],
            success_count=row['success_count'],
            failure_count=row['failure_count']
        )
"""
执行记录数据访问层
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from models.task_models import TaskExecution, TaskStatus

logger = logging.getLogger(__name__)


class ExecutionRepository:
    """执行记录数据访问对象"""

    def __init__(self, db_path: str = "data/taskscheduler.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration REAL,
                    result TEXT,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (task_id)
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

    def create_execution(self, execution: TaskExecution) -> bool:
        """创建执行记录"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO executions (
                        execution_id, task_id, status, start_time, end_time,
                        duration, result, error, retry_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution.execution_id,
                    execution.task_id,
                    execution.status,
                    execution.start_time,
                    execution.end_time,
                    execution.duration,
                    json.dumps(execution.result) if execution.result else None,
                    execution.error,
                    execution.retry_count
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to create execution: {e}")
            return False

    def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """获取执行记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM executions WHERE execution_id = ?
                """, (execution_id,))
                row = cursor.fetchone()

                if row:
                    return self._row_to_execution(row)
        except Exception as e:
            logger.error(f"Failed to get execution: {e}")
        return None

    def list_executions(self, task_id: Optional[str] = None,
                       status: Optional[str] = None,
                       page: int = 1, page_size: int = 20) -> List[TaskExecution]:
        """查询执行记录列表"""
        try:
            with self._get_connection() as conn:
                # 构建查询条件
                where_conditions = []
                params = []

                if task_id:
                    where_conditions.append("task_id = ?")
                    params.append(task_id)

                if status:
                    where_conditions.append("status = ?")
                    params.append(status)

                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # 分页查询
                offset = (page - 1) * page_size
                query = f"""
                    SELECT * FROM executions {where_clause}
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([page_size, offset])

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [self._row_to_execution(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list executions: {e}")
            return []

    def get_task_executions(self, task_id: str, limit: int = 10) -> List[TaskExecution]:
        """获取任务的执行记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM executions
                    WHERE task_id = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (task_id, limit))
                rows = cursor.fetchall()
                return [self._row_to_execution(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get task executions: {e}")
            return []

    def get_last_execution(self, task_id: str) -> Optional[TaskExecution]:
        """获取任务的最后一次执行记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM executions
                    WHERE task_id = ?
                    ORDER BY start_time DESC
                    LIMIT 1
                """, (task_id,))
                row = cursor.fetchone()
                return self._row_to_execution(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get last execution: {e}")
            return None

    def update_execution_status(self, execution_id: str, status: TaskStatus,
                               end_time: Optional[datetime] = None,
                               result: Optional[Dict[str, Any]] = None,
                               error: Optional[str] = None) -> bool:
        """更新执行状态"""
        try:
            with self._get_connection() as conn:
                updates = ["status = ?"]
                params = [status]

                if end_time:
                    updates.append("end_time = ?")
                    params.append(end_time)

                if result is not None:
                    updates.append("result = ?")
                    params.append(json.dumps(result))

                if error:
                    updates.append("error = ?")
                    params.append(error)

                # 计算执行时长
                if end_time:
                    updates.append("duration = (julianday(?) - julianday(start_time)) * 86400")
                    params.append(end_time)

                params.append(execution_id)

                query = f"UPDATE executions SET {', '.join(updates)} WHERE execution_id = ?"
                conn.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update execution status: {e}")
            return False

    def count_executions(self, task_id: Optional[str] = None,
                         status: Optional[str] = None) -> int:
        """统计执行记录数量"""
        try:
            with self._get_connection() as conn:
                where_conditions = []
                params = []

                if task_id:
                    where_conditions.append("task_id = ?")
                    params.append(task_id)

                if status:
                    where_conditions.append("status = ?")
                    params.append(status)

                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                query = f"SELECT COUNT(*) FROM executions {where_clause}"

                result = conn.execute(query, params).fetchone()[0]
                return result
        except Exception as e:
            logger.error(f"Failed to count executions: {e}")
            return 0

    def get_execution_statistics(self, task_id: str, days: int = 30) -> Dict[str, Any]:
        """获取执行统计信息"""
        try:
            with self._get_connection() as conn:
                # 最近N天的统计
                since_date = datetime.now() - timedelta(days=days)

                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total_executions,
                        COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
                        COUNT(CASE WHEN status = 'timeout' THEN 1 END) as timeout_count,
                        AVG(duration) as avg_duration,
                        MIN(duration) as min_duration,
                        MAX(duration) as max_duration
                    FROM executions
                    WHERE task_id = ? AND start_time >= ?
                """, (task_id, since_date))

                stats = cursor.fetchone()

                if stats and stats['total_executions'] > 0:
                    return {
                        'total_executions': stats['total_executions'],
                        'success_count': stats['success_count'],
                        'failed_count': stats['failed_count'],
                        'timeout_count': stats['timeout_count'],
                        'success_rate': (stats['success_count'] / stats['total_executions']) * 100,
                        'avg_duration': stats['avg_duration'],
                        'min_duration': stats['min_duration'],
                        'max_duration': stats['max_duration']
                    }
                else:
                    return {
                        'total_executions': 0,
                        'success_count': 0,
                        'failed_count': 0,
                        'timeout_count': 0,
                        'success_rate': 0,
                        'avg_duration': 0,
                        'min_duration': 0,
                        'max_duration': 0
                    }
        except Exception as e:
            logger.error(f"Failed to get execution statistics: {e}")
            return {}

    def cleanup_old_executions(self, days: int = 90) -> int:
        """清理旧的执行记录"""
        try:
            with self._get_connection() as conn:
                cutoff_date = datetime.now() - timedelta(days=days)
                cursor = conn.execute("""
                    DELETE FROM executions WHERE start_time < ?
                """, (cutoff_date,))
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {deleted_count} old execution records")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old executions: {e}")
            return 0

    def _row_to_execution(self, row) -> TaskExecution:
        """将数据库行转换为TaskExecution对象"""
        return TaskExecution(
            execution_id=row['execution_id'],
            task_id=row['task_id'],
            status=row['status'],
            start_time=datetime.fromisoformat(row['start_time']),
            end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
            duration=row['duration'],
            result=json.loads(row['result']) if row['result'] else None,
            error=row['error'],
            retry_count=row['retry_count'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
        )
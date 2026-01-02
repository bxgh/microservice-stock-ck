"""
任务执行日志服务

记录任务执行的开始、成功、失败等状态到MySQL数据库
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any
import aiomysql

logger = logging.getLogger(__name__)


class TaskLogger:
    """任务日志记录器"""
    
    def __init__(self, db_pool: aiomysql.Pool):
        """
        初始化任务日志记录器
        
        Args:
            db_pool: MySQL连接池
        """
        self.db_pool = db_pool
        self._lock = asyncio.Lock()
    
    async def log_start(
        self, 
        task_id: str, 
        task_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        记录任务开始
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            metadata: 元数据 (可选)
            
        Returns:
            int: 日志记录ID
        """
        async with self._lock:
            try:
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        sql = """
                            INSERT INTO task_execution_logs 
                            (task_id, task_name, status, start_time, metadata)
                            VALUES (%s, %s, 'RUNNING', NOW(), %s)
                        """
                        
                        metadata_json = json.dumps(metadata) if metadata else None
                        
                        await cursor.execute(sql, (task_id, task_name, metadata_json))
                        await conn.commit()
                        
                        log_id = cursor.lastrowid
                        logger.info(f"📝 Task started: {task_id} (log_id={log_id})")
                        return log_id
            except Exception as e:
                logger.error(f"Failed to log task start: {e}")
                return -1
    
    async def log_success(
        self, 
        log_id: int, 
        duration_seconds: float,
        exit_code: int = 0,
        container_id: Optional[str] = None
    ):
        """
        记录任务成功
        
        Args:
            log_id: 日志记录ID
            duration_seconds: 执行耗时(秒)
            exit_code: 退出码
            container_id: 容器ID (可选)
        """
        async with self._lock:
            try:
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        sql = """
                            UPDATE task_execution_logs
                            SET 
                                status = 'SUCCESS',
                                end_time = NOW(),
                                duration_seconds = %s,
                                exit_code = %s,
                                container_id = %s
                            WHERE id = %s
                        """
                        
                        await cursor.execute(
                            sql, 
                            (int(duration_seconds), exit_code, container_id, log_id)
                        )
                        await conn.commit()
                        
                        logger.info(
                            f"✓ Task completed successfully (log_id={log_id}, "
                            f"duration={duration_seconds:.1f}s)"
                        )
            except Exception as e:
                logger.error(f"Failed to log task success: {e}")
    
    async def log_failure(
        self, 
        log_id: int, 
        error_message: str,
        exit_code: int = -1,
        container_id: Optional[str] = None
    ):
        """
        记录任务失败
        
        Args:
            log_id: 日志记录ID
            error_message: 错误信息
            exit_code: 退出码
            container_id: 容器ID (可选)
        """
        async with self._lock:
            try:
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        sql = """
                            UPDATE task_execution_logs
                            SET 
                                status = 'FAILED',
                                end_time = NOW(),
                                duration_seconds = TIMESTAMPDIFF(
                                    SECOND, start_time, NOW()
                                ),
                                exit_code = %s,
                                error_message = %s,
                                container_id = %s
                            WHERE id = %s
                        """
                        
                        await cursor.execute(
                            sql, 
                            (exit_code, error_message[:5000], container_id, log_id)
                        )
                        await conn.commit()
                        
                        logger.error(
                            f"✗ Task failed (log_id={log_id}): {error_message[:100]}"
                        )
            except Exception as e:
                logger.error(f"Failed to log task failure: {e}")
    
    async def log_timeout(self, log_id: int):
        """
        记录任务超时
        
        Args:
            log_id: 日志记录ID
        """
        async with self._lock:
            try:
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        sql = """
                            UPDATE task_execution_logs
                            SET 
                                status = 'TIMEOUT',
                                end_time = NOW(),
                                duration_seconds = TIMESTAMPDIFF(
                                    SECOND, start_time, NOW()
                                ),
                                error_message = 'Task execution timeout'
                            WHERE id = %s
                        """
                        
                        await cursor.execute(sql, (log_id,))
                        await conn.commit()
                        
                        logger.warning(f"⏱ Task timeout (log_id={log_id})")
            except Exception as e:
                logger.error(f"Failed to log task timeout: {e}")
    
    async def get_task_history(
        self, 
        task_id: str, 
        limit: int = 20
    ) -> list:
        """
        获取任务执行历史
        
        Args:
            task_id: 任务ID
            limit: 返回记录数限制
            
        Returns:
            list: 执行历史记录
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    sql = """
                        SELECT 
                            id, task_id, task_name, status,
                            start_time, end_time, duration_seconds,
                            exit_code, error_message, container_id
                        FROM task_execution_logs
                        WHERE task_id = %s
                        ORDER BY start_time DESC
                        LIMIT %s
                    """
                    
                    await cursor.execute(sql, (task_id, limit))
                    rows = await cursor.fetchall()
                    
                    return rows
        except Exception as e:
            logger.error(f"Failed to get task history: {e}")
            return []
    
    async def get_task_stats(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务统计信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 统计信息
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    sql = """
                        SELECT * FROM task_execution_stats
                        WHERE task_id = %s
                    """
                    
                    await cursor.execute(sql, (task_id,))
                    row = await cursor.fetchone()
                    
                    return row
        except Exception as e:
            logger.error(f"Failed to get task stats: {e}")
            return None

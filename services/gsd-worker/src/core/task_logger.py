"""
任务执行日志记录器
"""

import logging
import aiomysql
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

CST = pytz.timezone('Asia/Shanghai')

class TaskLogger:
    """任务执行日志记录器"""
    
    def __init__(self, mysql_pool: aiomysql.Pool):
        self.mysql_pool = mysql_pool
        
    async def log_execution(self, 
                          task_name: str, 
                          status: str, 
                          records_processed: int, 
                          duration_seconds: float, 
                          execution_time: datetime,
                          details: str = None):
        """
        记录任务执行日志
        
        Args:
            task_name: 任务名称
            status: 执行状态 ('RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT')
            records_processed: 处理记录数
            duration_seconds: 执行耗时(秒)
            execution_time: 执行时间
            details: 详情描述
        """
        try:
            async with self.mysql_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    query = """
                        INSERT INTO sync_execution_logs 
                        (task_name, status, records_processed, duration_seconds, execution_time, details)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    await cursor.execute(query, (
                        task_name, 
                        status, 
                        records_processed, 
                        duration_seconds, 
                        execution_time, 
                        details
                    ))
                    await conn.commit()
                    logger.info(f"📝 已写入执行日志: {task_name} - {status}")
                    
        except aiomysql.Error as e:
            logger.error(f"❌ 数据库操作失败: {e}")
        except Exception as e:
            logger.error(f"❌ 写入执行日志未知错误: {e}")

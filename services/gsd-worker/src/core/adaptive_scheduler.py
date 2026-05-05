"""
K线同步自适应调度器

实现"历史预测 + 智能等待 + 信号量轮询"机制，确保在云端数据完成后尽早启动同步。

设计文档: docs/architecture/task_scheduling/11_kline_sync_optimization.md
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

import aiomysql
import pytz

logger = logging.getLogger(__name__)

# 时区配置
CST = pytz.timezone('Asia/Shanghai')


class CloudSyncException(Exception):
    """云端同步异常基类"""
    pass


class CloudSyncFailedException(CloudSyncException):
    """云端采集失败异常"""
    pass


class CloudSyncTimeoutException(CloudSyncException):
    """云端采集超时异常"""
    pass


class DataVolumeAnomalyException(CloudSyncException):
    """数据量异常"""
    pass


class AdaptiveKLineSyncScheduler:
    """K线同步自适应调度器"""
    
    def __init__(self, mysql_pool: aiomysql.Pool):
        """
        初始化调度器
        
        Args:
            mysql_pool: MySQL连接池（连接到腾讯云MySQL alwaysup库）
        """
        self.mysql_pool = mysql_pool
        
        # 从环境变量读取配置参数
        self.history_buffer_min = int(os.getenv('KLINE_SYNC_HISTORY_BUFFER_MIN', '5'))
        self.sleep_check_interval_min = int(os.getenv('KLINE_SYNC_SLEEP_CHECK_INTERVAL_MIN', '15'))
        self.poll_interval_min = int(os.getenv('KLINE_SYNC_POLL_INTERVAL_MIN', '2'))
        self.timeout_time_str = os.getenv('KLINE_SYNC_TIMEOUT_TIME', '21:00')
        self.min_records = int(os.getenv('KLINE_SYNC_MIN_RECORDS', '4800'))
        
        logger.info(f"📋 调度器配置: 历史缓冲={self.history_buffer_min}分钟, "
                   f"轮询间隔={self.poll_interval_min}分钟, "
                   f"最小记录数={self.min_records}, "
                   f"超时时间={self.timeout_time_str}")
    
    async def predict_wait_window(self) -> Optional[datetime]:
        """
        历史预测阶段：查询前一交易日的完成时间，计算目标观察窗口
        
        Returns:
            目标观察窗口时间（CST时区），如果无历史记录则返回None
        """
        logger.info("📊 [阶段1] 历史预测 - 查询前一交易日完成时间...")
        
        try:
            async with self.mysql_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT updated_at, total_count
                        FROM sync_progress 
                        WHERE task_name = 'full_market_sync' 
                          AND status = 'completed' 
                        ORDER BY updated_at DESC 
                        LIMIT 1
                    """
                    await cursor.execute(query)
                    result = await cursor.fetchone()
                    
                    if not result:
                        logger.warning("⚠️  无历史记录，将直接进入轮询模式")
                        return None
                    
                    last_completion_time = result['updated_at']
                    last_records = result.get('total_count', 0)
                    
                    # 确保时间带有时区信息
                    if last_completion_time.tzinfo is None:
                        last_completion_time = CST.localize(last_completion_time)
                    else:
                        last_completion_time = last_completion_time.astimezone(CST)
                    
                    # 计算目标观察窗口 = 历史完成时间 - 缓冲时间
                    target_window = last_completion_time - timedelta(minutes=self.history_buffer_min)
                    
                    # 使用今天的日期 + 历史的时间
                    now = datetime.now(CST)
                    target_window_today = now.replace(
                        hour=target_window.hour,
                        minute=target_window.minute,
                        second=0,
                        microsecond=0
                    )
                    
                    logger.info(f"✓ 历史完成时间: {last_completion_time.strftime('%Y-%m-%d %H:%M:%S')} "
                               f"(记录数: {last_records})")
                    logger.info(f"✓ 目标观察窗口: {target_window_today.strftime('%H:%M:%S')} "
                               f"(提前{self.history_buffer_min}分钟)")
                    
                    return target_window_today
                    
        except Exception as e:
            logger.error(f"❌ 查询历史记录失败: {e}", exc_info=True)
            return None
    
    async def adaptive_wait(self, target_time: Optional[datetime]):
        """
        智能等待阶段：长休眠 + 定期检查
        
        Args:
            target_time: 目标观察窗口时间，如果为None则跳过等待
        """
        if target_time is None:
            logger.info("💤 [阶段2] 智能等待 - 跳过（无历史记录）")
            return
        
        now = datetime.now(CST)
        
        if now >= target_time:
            logger.info(f"💤 [阶段2] 智能等待 - 跳过（已过目标时间 {target_time.strftime('%H:%M:%S')}）")
            return
        
        wait_seconds = (target_time - now).total_seconds()
        logger.info(f"💤 [阶段2] 智能等待 - 等待至 {target_time.strftime('%H:%M:%S')} "
                   f"(约 {wait_seconds/60:.1f} 分钟)")
        
        # 长休眠期间，每隔一定时间检查一次是否提前完成
        check_interval_seconds = self.sleep_check_interval_min * 60
        
        while datetime.now(CST) < target_time:
            # 检查是否有提前完成的信号
            signal = await self._check_today_signal()
            if signal and signal['status'] == 'completed':
                logger.info(f"⏰ 检测到提前完成信号！云端于 {signal['updated_at']} 完成")
                return
            
            # 计算下次检查时间
            remaining = (target_time - datetime.now(CST)).total_seconds()
            sleep_time = min(check_interval_seconds, remaining)
            
            if sleep_time > 0:
                logger.info(f"💤 休眠 {sleep_time/60:.1f} 分钟后再检查...")
                await asyncio.sleep(sleep_time)
        
        logger.info(f"⏰ 已到达目标观察窗口 {target_time.strftime('%H:%M:%S')}")
    
    async def poll_for_signal(self) -> Tuple[str, int]:
        """
        信号量轮询阶段：高频检查云端完成信号
        
        Returns:
            (完成时间字符串, 记录数)
            
        Raises:
            CloudSyncFailedException: 云端采集失败
            CloudSyncTimeoutException: 云端采集超时
            DataVolumeAnomalyException: 数据量异常
        """
        logger.info(f"🔍 [阶段3] 信号量轮询 - 每 {self.poll_interval_min} 分钟检查一次...")
        
        # 解析超时时间
        timeout_hour, timeout_minute = map(int, self.timeout_time_str.split(':'))
        now = datetime.now(CST)
        timeout_time = now.replace(hour=timeout_hour, minute=timeout_minute, second=0, microsecond=0)
        
        poll_count = 0
        
        while True:
            poll_count += 1
            signal = await self._check_today_signal()
            
            if signal:
                status = signal['status']
                updated_at = signal['updated_at']
                total_count = signal.get('total_count', 0)
                
                if status == 'failed':
                    error_msg = signal.get('error_message', '未知错误')
                    logger.error(f"❌ 云端采集失败: {error_msg}")
                    raise CloudSyncFailedException(f"云端采集失败: {error_msg}")
                
                elif status == 'completed':
                    logger.info(f"✅ 发现 completed 信号！")
                    logger.info(f"   完成时间: {updated_at}")
                    logger.info(f"   记录总数: {total_count}")
                    
                    # 数据量校验
                    if total_count < self.min_records:
                        logger.warning(f"⚠️  数据量异常: {total_count} < {self.min_records}")
                        raise DataVolumeAnomalyException(
                            f"云端采集记录数异常: {total_count} < {self.min_records}"
                        )
                    
                    logger.info(f"✓ 阈值校验通过: {total_count} >= {self.min_records}")
                    return (updated_at, total_count)
                
                else:
                    logger.info(f"🔍 第{poll_count}次检查: 状态={status}, 继续等待...")
            else:
                logger.info(f"🔍 第{poll_count}次检查: 未发现今日记录")
            
            # 检查是否超时
            if datetime.now(CST) >= timeout_time:
                break
                
            # 等待下次轮询
            await asyncio.sleep(self.poll_interval_min * 60)
        
        # 超时
        logger.error(f"❌ 超过 {self.timeout_time_str} 仍未发现 completed 信号")
        raise CloudSyncTimeoutException(f"云端采集超时（超过 {self.timeout_time_str}）")
    
    async def _check_today_signal(self) -> Optional[Dict[str, Any]]:
        """
        检查今日的云端完成信号
        
        Returns:
            信号字典，包含 status, updated_at, total_records, error_message
            如果今日无记录则返回 None
        """
        try:
            async with self.mysql_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT status, total_count, updated_at
                        FROM sync_progress 
                        WHERE task_name = 'full_market_sync' 
                          AND DATE(updated_at) = CURDATE()
                        ORDER BY updated_at DESC 
                        LIMIT 1
                    """
                    await cursor.execute(query)
                    result = await cursor.fetchone()
                    
                    if result:
                        # 格式化时间为字符串
                        result['updated_at'] = result['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
                    
                    return result
                    
        except Exception as e:
            logger.warning(f"检查今日信号失败: {e}")
            return None
    
    async def execute(self) -> Tuple[str, int]:
        """
        执行完整的自适应调度流程
        
        Returns:
            (云端完成时间, 记录数)
            
        Raises:
            CloudSyncException: 各种云端同步异常
        """
        logger.info("=" * 80)
        logger.info("🚀 启动 K线同步自适应调度器")
        logger.info("=" * 80)
        
        start_time = datetime.now(CST)
        
        try:
            # 阶段1: 历史预测
            target_window = await self.predict_wait_window()
            
            # 阶段2: 智能等待
            await self.adaptive_wait(target_window)
            
            # 阶段3: 信号量轮询
            cloud_completion_time, total_records = await self.poll_for_signal()
            
            elapsed = (datetime.now(CST) - start_time).total_seconds()
            logger.info("=" * 80)
            logger.info(f"✅ 调度完成！总耗时: {elapsed/60:.1f} 分钟")
            logger.info(f"   云端完成时间: {cloud_completion_time}")
            logger.info(f"   记录总数: {total_records}")
            logger.info("=" * 80)
            
            return (cloud_completion_time, total_records)
            
        except CloudSyncException:
            # 重新抛出已知的云端同步异常
            raise
        except Exception as e:
            logger.error(f"❌ 调度器执行失败: {e}", exc_info=True)
            raise CloudSyncException(f"调度器执行失败: {e}") from e

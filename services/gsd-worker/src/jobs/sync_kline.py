"""
K线同步任务入口

供 task-orchestrator 调用的临时任务
"""

import sys
import asyncio
import logging
import argparse
from core.sync_service import KLineSyncService
from core.adaptive_scheduler import (
    AdaptiveKLineSyncScheduler,
    CloudSyncException
)
from core.task_logger import TaskLogger
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main(mode: str = 'adaptive', shard_index: int = None):
    """
    K线同步主函数
    
    Args:
        mode: 'adaptive' (自适应调度) | 'direct' (直接同步，用于测试)
        shard_index: 分片索引 (0/1/2)，None 表示全量同步
        
    Returns:
        int: 退出码 (0: 成功, 1: 失败)
    """
    shard_info = f" (Shard {shard_index})" if shard_index is not None else ""
    logger.info(f"启动K线同步任务 (模式={mode}{shard_info})")
    
    service = KLineSyncService()
    await service.initialize()
    
    task_logger = TaskLogger(service.mysql_pool)
    start_time = datetime.now()
    
    try:
        cloud_completion_time = None
        total_records = 0
        
        if mode == 'adaptive':
            # 自适应调度模式
            logger.info("🔧 使用自适应调度模式")
            scheduler = AdaptiveKLineSyncScheduler(service.mysql_pool)
            
            try:
                # 等待云端完成信号
                cloud_completion_time, total_records = await scheduler.execute()
                logger.info(f"✓ 云端数据已就绪，开始本地同步...")
            except CloudSyncException as e:
                logger.error(f"❌ 云端同步异常: {e}")
                duration = (datetime.now() - start_time).total_seconds()
                await task_logger.log_execution(
                    "kline_daily_sync", 
                    "FAILED", 
                    0, 
                    duration, 
                    start_time, 
                    f"云端同步异常: {str(e)}"
                )
                return 1
        else:
            # 直接同步模式（用于测试或手动触发）
            logger.info("🔧 使用直接同步模式（跳过云端信号检测）")
        
        # 单机模式：智能增量同步 (支持分片)
        await service.sync_smart_incremental(shard_index=shard_index)
        # 同步复权因子
        await service.sync_adjust_factors()
        
        # 成功日志由 sync_service 内部记录，这里不需要重复记录，以免重复
        logger.info("✅ K线同步任务完成")
        return 0
    except Exception as e:
        logger.error(f"❌ K线同步任务失败: {e}", exc_info=True)
        duration = (datetime.now() - start_time).total_seconds()
        try:
            await task_logger.log_execution(
                "kline_daily_sync", 
                "FAILED", 
                0, 
                duration, 
                start_time, 
                f"任务执行异常: {str(e)}"
            )
        except Exception as log_err:
            logger.error(f"无法写入失败日志: {log_err}")
        return 1
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K线同步任务")
    parser.add_argument("--mode", type=str, default="adaptive", 
                       choices=["adaptive", "direct"],
                       help="同步模式: adaptive(自适应调度) 或 direct(直接同步)")
    parser.add_argument("--shard-index", type=int, default=None,
                       help="分片索引 (0/1/2)，不指定则全量同步")
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(args.mode, args.shard_index))
    sys.exit(exit_code)

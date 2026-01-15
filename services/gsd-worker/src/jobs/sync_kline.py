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

async def main(mode: str = 'adaptive', shard_index: int = None, date: str = None):
    """
    K线同步主函数
    
    Args:
        mode: 'adaptive' (自适应调度) | 'direct' (直接同步)
        shard_index: 分片索引 (0/1/2)，None 表示全量同步
        date: 指定日期 (YYYYMMDD)，不为空时触发按日期同步
    """
    start_time = datetime.now()
    shard_info = f" (Shard {shard_index})" if shard_index is not None else ""
    date_info = f", 日期={date}" if date else ""
    
    logger.info(f"启动K线同步任务 (模式={mode}{shard_info}{date_info})")
    
    service = KLineSyncService()
    await service.initialize()
    
    task_logger = TaskLogger(service.mysql_pool)
    start_time = datetime.now()
    
    try:
        # 优先处理指定日期同步（现在统一使用智能同步）
        if date:
            logger.info(f"🔧 收到日期参数 {date}，使用智能自愈同步（自动检测并修复不一致数据）")
        
        # 统一使用智能增量同步（自带自愈功能）
        await service.sync_smart_incremental()
        
        # 同步复权因子
        await service.sync_adjust_factors()
        
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
    parser.add_argument("--date", type=str, default=None,
                       help="指定日期 (YYYYMMDD 或 YYYY-MM-DD)")
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(args.mode, args.shard_index, args.date))
    sys.exit(exit_code)

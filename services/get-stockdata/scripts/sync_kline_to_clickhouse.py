"""
MySQL到ClickHouse K线数据同步脚本
支持全量和增量同步
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# 将 src加入 python path 以便导入 core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.sync_service import KLineSyncService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='K线数据同步脚本')
    parser.add_argument('--mode', 
                        choices=['full', 'incremental', 'smart', 'created_at'], 
                        default='smart',
                        help='同步模式：full=全量，incremental=增量（基于天数），'
                             'smart=智能增量（基于最大日期），created_at=基于创建时间戳')
    parser.add_argument('--days', type=int, default=7,
                        help='增量同步天数（仅在incremental模式下有效，默认7天）')
    parser.add_argument('--hours', type=int, default=48,
                        help='回溯小时数（仅在created_at模式下有效，默认48小时）')
    parser.add_argument('--start-time', type=str,
                        help='指定同步开始时间（格式：YYYY-MM-DD HH:MM:SS），仅在created_at模式下有效')
    parser.add_argument('--batch-size', type=int, default=10000,
                        help='全量/增量同步批次大小（默认10000）')
    
    args = parser.parse_args()
    
    sync_service = KLineSyncService()
    
    try:
        await sync_service.initialize()
        
        if args.mode == 'full':
            await sync_service.sync_full(batch_size=args.batch_size)
        elif args.mode == 'smart':
            await sync_service.sync_smart_incremental()
        elif args.mode == 'created_at':
            start_dt = None
            if args.start_time:
                try:
                    start_dt = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    logger.error("无效的时间格式，请使用 YYYY-MM-DD HH:MM:SS")
                    return
            
            await sync_service.sync_by_created_at(
                lookback_hours=args.hours, 
                batch_size=args.batch_size,
                start_time=start_dt
            )
        else:  # incremental
            await sync_service.sync_incremental(days=args.days)
        
    except Exception as e:
        logger.error(f"同步失败: {e}", exc_info=True)
        raise
    finally:
        await sync_service.close()


if __name__ == "__main__":
    asyncio.run(main())

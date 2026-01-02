"""
数据质量检查任务入口
"""

import sys
import asyncio
import logging
import argparse
import json
from datetime import datetime
from core.data_quality_service import DataQualityService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main(deep_scan: bool = False, batch_size: int = 100) -> int:
    """
    数据质量检查主函数
    """
    logger.info("启动数据质量检查任务...")
    
    service = DataQualityService()
    await service.initialize()
    
    try:
        # 1. 执行每日常规检查 (Timeliness, Consistency, Duplicates)
        logger.info("执行常规质量检查...")
        daily_report = await service.run_daily_check()
        logger.info(f"常规检查完成: {daily_report['overall_status']}")
        
        # 2. 如果开启了深度扫描，或者作为质量检查的一部分
        if deep_scan:
            logger.info(f"开始执行深度扫描 (Batch Size: {batch_size})...")
            scan_report = await service.run_universe_scan_batch(batch_size=batch_size)
            logger.info(f"深度扫描完成: {scan_report['message']}")
            
        logger.info("数据质量检查任务结束")
        return 0
    except Exception as e:
        logger.error(f"数据质量检查任务失败: {e}", exc_info=True)
        return 1
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数据质量检查任务")
    parser.add_argument("--deep", action="store_true", help="开启全市场深度扫描")
    parser.add_argument("--batch", type=int, default=100, help="深度扫描批次大小")
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(args.deep, args.batch))
    sys.exit(exit_code)

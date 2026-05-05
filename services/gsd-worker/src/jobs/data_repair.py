"""
数据修复任务入口
"""

import sys
import asyncio
import logging
import argparse
from core.data_repair_service import DataRepairService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main(limit: int = 10) -> int:
    """
    数据修复主函数
    """
    logger.info("启动数据修复任务...")
    
    service = DataRepairService()
    await service.initialize()
    
    try:
        # 执行批量修复
        await service.run_repair_batch(limit=limit)
        
        logger.info("数据修复任务结束")
        return 0
    except Exception as e:
        logger.error(f"数据修复任务失败: {e}", exc_info=True)
        return 1
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数据修复任务")
    parser.add_argument("--limit", type=int, default=10, help="单次修复的最大股票数")
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(args.limit))
    sys.exit(exit_code)

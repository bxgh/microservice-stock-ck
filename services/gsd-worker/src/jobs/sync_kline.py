"""
K线同步任务入口

供 task-orchestrator 调用的临时任务
"""

import sys
import asyncio
import logging
import argparse
from core.sync_service import KLineSyncService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main(shard_index: int = 0, total_shards: int = 1):
    """
    K线同步主函数
    
    Args:
        shard_index: 分片索引 (0-based)
        total_shards: 总分片数
    """
    logger.info(f"启动K线同步任务 (分片 {shard_index+1}/{total_shards})")
    
    service = KLineSyncService()
    await service.initialize()
    
    try:
        # 分片模式：并行处理
        if total_shards > 1:
            logger.info(f"分片模式: {shard_index+1}/{total_shards}")
            await service.sync_by_shard(shard_index, total_shards)
        else:
            # 单机模式：智能增量同步
            await service.sync_smart_incremental()
        
        logger.info("K线同步任务完成")
        return 0
    except Exception as e:
        logger.error(f"K线同步任务失败: {e}", exc_info=True)
        return 1
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K线同步任务")
    parser.add_argument("--shard", type=int, default=0, help="分片索引")
    parser.add_argument("--total", type=int, default=1, help="总分片数")
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(args.shard, args.total))
    sys.exit(exit_code)

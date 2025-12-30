"""
MySQL到ClickHouse 复权因子同步脚本
"""
import asyncio
import logging
import sys
import os

# 将 src 加入 python path 以便导入 core
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
    
    parser = argparse.ArgumentParser(description='复权因子同步脚本')
    parser.add_argument('--batch-size', type=int, default=5000,
                        help='同步批次大小（默认5000）')
    
    args = parser.parse_args()
    
    sync_service = KLineSyncService()
    
    try:
        await sync_service.initialize()
        await sync_service.sync_adjust_factors(batch_size=args.batch_size)
    except Exception as e:
        logger.error(f"同步失败: {e}", exc_info=True)
        raise
    finally:
        await sync_service.close()


if __name__ == "__main__":
    asyncio.run(main())

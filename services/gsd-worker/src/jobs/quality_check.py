"""
数据质量检测任务入口
"""

import sys
import asyncio
import logging
from core.data_quality_service import DataQualityService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """数据质量检测主函数"""
    logger.info("启动数据质量检测任务")
    
    service = DataQualityService()
    await service.initialize()
    
    try:
        result = await service.daily_check()
        logger.info(f"质量检测完成: {result}")
        return 0
    except Exception as e:
        logger.error(f"质量检测失败: {e}", exc_info=True)
        return 1
    finally:
        await service.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

"""
Weekly Audit Job Entry Point
"""
import sys
import asyncio
import logging
from datetime import datetime

from core.audit_service import WeeklyAuditService
from core.task_logger import TaskLogger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🛡️ 启动每周深度审计任务...")
    service = WeeklyAuditService()
    await service.initialize()
    
    try:
        await service.run_full_audit()
        logger.info("✅ 每周深度审计任务完成")
        return 0
    except Exception as e:
        logger.error(f"❌ 每周深度审计任务失败: {e}")
        return 1
    finally:
        await service.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

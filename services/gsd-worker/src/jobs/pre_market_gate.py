"""
Pre-Market Gate Check Job Entry Point
"""
import sys
import asyncio
import logging

from core.pre_market_gate_service import PreMarketGateService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🛡️ 启动盘前数据门禁校验 (Gate-1)...")
    service = PreMarketGateService()
    await service.initialize()
    
    try:
        await service.run_gate_check()
        logger.info("✅ 盘前校验任务执行完成")
        return 0
    except Exception as e:
        logger.error(f"❌ 盘前校验任务执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        await service.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

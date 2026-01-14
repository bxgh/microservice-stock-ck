import asyncio
import logging
import sys
from core.post_market_gate_service import PostMarketGateService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/post_market_gate.log")
    ]
)

logger = logging.getLogger("PostMarketGateJob")

async def main():
    logger.info("🛡️ Starting Post-Market Data Gate (Gate-3)...")
    
    service = PostMarketGateService()
    try:
        await service.initialize()
        report = await service.run_gate_check()
        logger.info(f"✅ Gate-3 Audit Complete. Status: {report['status']}")
    except Exception as e:
        logger.error(f"❌ Gate-3 Job Failed: {e}", exc_info=True)
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())

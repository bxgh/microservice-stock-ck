import asyncio
import os
import logging
from core.pre_market_gate_service import PreMarketGateService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pre_market_gate():
    os.environ["ENVIRONMENT"] = "development"
    # 强制本地隧道端口
    os.environ["GSD_DB_PORT"] = "36301"
    
    service = PreMarketGateService()
    await service.initialize()
    
    try:
        logger.info("TEST: Running Gate-1 Check...")
        report = await service.run_gate_check()
        logger.info(f"TEST RESULT: {report}")
        
        if report['status'] in ["SUCCESS", "WARNING"]:
            logger.info("✅ Test Passed (Status reasonable)")
        else:
            logger.error("❌ Test Failed (Unexpected status)")
            
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(test_pre_market_gate())

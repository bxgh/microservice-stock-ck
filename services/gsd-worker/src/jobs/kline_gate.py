import asyncio
import logging
import sys
import argparse
from core.post_market_gate_service import PostMarketGateService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("KlineGateJob")

async def main():
    parser = argparse.ArgumentParser(description="K线与复权因子独立审计门禁 (Gate-3.1)")
    parser.add_argument("--date", type=str, help="目标交易日期 (YYYY-MM-DD 或 YYYYMMDD)")
    args = parser.parse_args()

    logger.info("🛡️ Starting Standalone K-Line & Adjust Factor Gate (Gate-3.1)...")
    
    service = PostMarketGateService()
    try:
        await service.initialize()
        report = await service.run_kline_standalone_check(args.date)
        
        icon = "✅" if report['status'] == "SUCCESS" else "⚠️"
        logger.info(f"{icon} Kline Gate Audit Complete.")
        logger.info(f"📊 K线覆盖率: {report['kline_rate']}%")
        logger.info(f"📊 复权因子覆盖率: {report['adj_factor_rate']}%")
        logger.info(f"🚨 质量异常数: {report['quality_errors']}")
        
        if report['actions_taken']:
            logger.info(f"⚡ 响应动作: {', '.join(report['actions_taken'])}")
            
    except Exception as e:
        logger.error(f"❌ Kline Gate Job Failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())

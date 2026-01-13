import asyncio
import logging
import sys
from src.core.collector.intraday_tick_collector import IntradayTickCollector, setup_signals

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/intraday_tick_collector.log")
    ]
)

logger = logging.getLogger("IntradayTickMain")

async def main():
    logger.info("🌟 HS300 Intraday Tick Collector Starting...")
    
    collector = IntradayTickCollector()
    setup_signals(collector)
    
    try:
        await collector.run()
    except Exception as e:
        logger.critical(f"💥 Collector crashed unexpectedly: {e}", exc_info=True)
    finally:
        await collector.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")

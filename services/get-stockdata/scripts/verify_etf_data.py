"""
Verify ETF Data Fetching via Akshare
"""
import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from services.stock_pool.hot_sectors_manager import HotSectorsManager
from services.stock_pool.config_manager import StockPoolConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting ETF data verification...")
    
    # Initialize managers
    config_manager = StockPoolConfigManager()
    await config_manager.load_config()
    
    manager = HotSectorsManager(config_manager)
    
    # Test fetching specific ETF
    etf_code = "512480" # 半导体ETF
    logger.info(f"Fetching data for ETF {etf_code}...")
    
    try:
        stocks = await asyncio.to_thread(manager._get_etf_stocks_sync, etf_code, 5)
        logger.info(f"Successfully fetched {len(stocks)} stocks: {stocks}")
        
        if not stocks:
            logger.error("Fetched empty list!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Failed to fetch ETF data: {e}")
        sys.exit(1)
        
    logger.info("✅ Verification successful!")

if __name__ == "__main__":
    asyncio.run(main())

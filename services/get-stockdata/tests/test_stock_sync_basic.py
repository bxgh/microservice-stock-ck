
import asyncio
import os
import sys
import logging

# Add src to path
# Add paths for Docker (/app/src) and Host
if os.path.exists("/app/src"):
    sys.path.append("/app/src")
else:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
    sys.path.append(os.getcwd())

try:
    from services.stock_code_client import StockCodeClient
except ImportError:
    try:
        from src.services.stock_code_client import StockCodeClient
    except ImportError:
        # Fallback
        from services.get_stockdata.src.services.stock_code_client import StockCodeClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sync():
    # Use configuration from Environment or default to Host Localhost
    api_url = os.getenv("STOCK_API_URL", "http://localhost:8111/api/v1")
    os.environ["STOCK_API_URL"] = api_url
    
    logger.info(f"Using STOCK_API_URL: {api_url}")
    
    client = StockCodeClient()
    await client.initialize()
    
    try:
        logger.info("Fetching all stocks...")
        stocks = await client.get_all_stocks(limit=10)
        
        if not stocks:
            logger.error("❌ Returned empty list!")
            return
            
        logger.info(f"✅ Returned {len(stocks)} stocks.")
        for s in stocks:
            logger.info(f"Code: {s.stock_code}, Name: {s.stock_name}, Industry: {s.industry}, Exchange: {s.exchange}")
            
        # Check if industry is missing (Expected None)
        if stocks[0].industry is None:
            logger.info("⚠️ Industry is missing as expected (needs enrichment).")
        else:
            logger.info("🎉 Industry is present!")
            
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_sync())

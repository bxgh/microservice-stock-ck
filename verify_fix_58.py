import asyncio
import aiohttp
import logging
import os
import sys

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Mock setup to run TickFetcher
sys.path.append("/app/src")
# Ensure libs is in path too if needed, though Dockerfile ENV should handle it if built correctly. 
# But safe to add.
sys.path.append("/app/libs/gsd-shared")

try:
    from core.tick_fetcher import TickFetcher
except ImportError as e:
    logging.error(f"Import failed: {e}")
    sys.exit(1)

async def main():
    # Server 58 moo-tdx api is locally available? 
    # Usually api is at localhost:8003 on the node running gsd-worker if network=host.
    api_url = "http://127.0.0.1:8003"
    
    stock_code = "000001"
    trade_date = "20251202"
    
    logging.info(f"Testing TickFetcher for {stock_code} on {trade_date} with API: {api_url}")
    
    async with aiohttp.ClientSession() as session:
        fetcher = TickFetcher(session, api_url)
        data = await fetcher.fetch(stock_code, trade_date)
        
        logging.info(f"Total ticks fetched: {len(data)}")
        if data:
            logging.info(f"First tick: {data[0].get('time')}")
            logging.info(f"Last tick: {data[-1].get('time')}")
            
            # Simple continuity check
            times = set()
            for row in data:
                t = row.get('time')
                if t:
                    times.add(t[:5]) # HH:MM
            logging.info(f"Active minutes: {len(times)}")

if __name__ == "__main__":
    asyncio.run(main())

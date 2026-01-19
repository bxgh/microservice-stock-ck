import asyncio
import aiohttp
import logging
import os
import sys
from typing import List, Dict, Any

# Mock setup to run TickFetcher
sys.path.append("/app/src")

from core.tick_fetcher import TickFetcher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    # Use localhost:8003
    api_url = "http://127.0.0.1:8003"
    
    stock_code = "000001"
    trade_date = "20251202"
    
    print(f"Testing TickFetcher for {stock_code} on {trade_date} with API: {api_url}")
    
    async with aiohttp.ClientSession() as session:
        fetcher = TickFetcher(session, api_url)
        data = await fetcher.fetch(stock_code, trade_date)
        
        print(f"Total ticks fetched: {len(data)}")
        if data:
            print(f"First tick: {data[0].get('time')}")
            print(f"Last tick: {data[-1].get('time')}")
            
            # Simple continuity check
            times = set()
            for row in data:
                t = row.get('time')
                if t:
                    times.add(t[:5]) # HH:MM
            print(f"Active minutes: {len(times)}")

if __name__ == "__main__":
    asyncio.run(main())

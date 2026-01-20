import asyncio
import aiohttp
import os
import sys

# Mock setup to run TickFetcher
sys.path.append("/app/src")
sys.path.append("/app/libs/gsd-shared")

try:
    from core.tick_fetcher import TickFetcher
    print("Import successful", flush=True)
except ImportError as e:
    print(f"Import failed: {e}", flush=True)
    sys.exit(1)

async def main():
    api_url = "http://127.0.0.1:8003"
    stock_code = "000001"
    trade_date = "20251202"
    
    print(f"Testing TickFetcher for {stock_code} on {trade_date} with API: {api_url}", flush=True)
    
    async with aiohttp.ClientSession() as session:
        fetcher = TickFetcher(session, api_url)
        print("Fetcher initialized, starting fetch...", flush=True)
        data = await fetcher.fetch(stock_code, trade_date)
        
        print(f"Total ticks fetched: {len(data)}", flush=True)
        if data:
            print(f"First tick: {data[0].get('time')}", flush=True)
            print(f"Last tick: {data[-1].get('time')}", flush=True)
            
            times = set()
            for row in data:
                t = row.get('time')
                if t:
                    times.add(t[:5])
            print(f"Active minutes: {len(times)}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())

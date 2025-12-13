
import asyncio
import sys
import os

# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from adapters.stock_data_provider import data_provider
from config.settings import settings

async def main():
    print(f"--- Configuration ---")
    print(f"Service URL: {settings.stockdata_service_url}")
    print(f"---------------------")

    print("\n[TestCase 1] Test Real-time Quotes for 600519 (Moutai) and 000001 (PingAn)")
    try:
        # Assuming get-stockdata is running and these codes are valid
        codes = ['600519', '000001']
        df = await data_provider.get_realtime_quotes(codes)
        
        if not df.empty:
            print(f"SUCCESS: Fetched {len(df)} records.")
            print(df[['code', 'name', 'price', 'change_pct', 'timestamp']])
        else:
            print("WARNING: Returned empty DataFrame. Is the market open or service reachable?")
            
    except Exception as e:
        print(f"ERROR: Failed to fetch quotes. Reason: {e}")

    print("\n[TestCase 2] Test Stock List (Limit 5)")
    try:
        stocks = await data_provider.get_all_stocks(limit=5)
        if stocks:
            print(f"SUCCESS: Fetched {len(stocks)} stocks.")
            for s in stocks:
                print(f" - {s.get('code')} {s.get('name')} ({s.get('exchange')})")
        else:
             print("WARNING: Returned empty list.")
    except Exception as e:
        print(f"ERROR: Failed to fetch stock list. Reason: {e}")

    await data_provider.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

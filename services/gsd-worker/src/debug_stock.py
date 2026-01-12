import asyncio
import os
import sys
from mootdx.quotes import Quotes

async def debug_stock(code, date):
    print(f"Debugging {code} for date {date}")
    
    # Use the same IP as the pool if possible, or just auto
    client = Quotes.factory(market='std', bestip=True)
    
    # Try different offsets to map out the data
    offsets = [0, 2000, 4000, 6000, 8000, 10000]
    
    for start in offsets:
        print(f"--- Querying start={start} offset=100 ---")
        try:
            data = client.transactions(symbol=code, date=date, start=start, offset=100)
            if data is not None and not data.empty:
                print(f"Rows: {len(data)}")
                print(f"Time Range: {data['time'].min()} - {data['time'].max()}")
                print("First 3 rows:")
                print(data.head(3))
            else:
                print("No data (None or empty)")
        except Exception as e:
            print(f"Error: {e}")
            
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_stock.py <code> <date>")
        sys.exit(1)
        
    code = sys.argv[1]
    date = sys.argv[2]
    loop = asyncio.new_event_loop()
    loop.run_until_complete(debug_stock(code, date))

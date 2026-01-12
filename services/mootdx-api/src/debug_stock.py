import asyncio
import os
import sys
from mootdx.quotes import Quotes

async def debug_stock(code, date):
    print(f"Debugging {code} for date {date}")
    
    ips = [
        # Huawei (known shallow)
        ('175.6.5.153', 7709),
        
        # QP (known deep usually)
        ('119.147.212.81', 7709),
        ('47.107.64.168', 7709),
        ('124.71.187.122', 7709), 
        ('119.29.19.242', 7709),
        ('123.60.84.66', 7709),
        ('106.14.95.63', 7709),
        ('113.105.142.136', 7709),
        ('123.125.108.23', 7709)
    ]
    
    for ip, port in ips:
        print(f"\nTesting Server {ip}:{port}...")
        try:
            client = Quotes.factory(market='std', bestip=False, server=(ip, port))
            
            # Check 6000 offset (where we lost data before)
            # and a deeper one 8000
            for start in [5000, 6000, 8000]:
                data = client.transactions(symbol=code, date=date, start=start, offset=100)
                if data is not None and not data.empty:
                    print(f"  [Offset {start}]: OK | {len(data)} rows | Time: {data['time'].min()} - {data['time'].max()}")
                else:
                    print(f"  [Offset {start}]: NO DATA")
        except Exception as e:
            print(f"  Server {ip} failed: {e}")
            
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_stock.py <code> <date>")
        sys.exit(1)
        
    code = sys.argv[1]
    date = sys.argv[2]
    loop = asyncio.new_event_loop()
    loop.run_until_complete(debug_stock(code, date))

from mootdx.quotes import Quotes
import logging

logging.basicConfig(level=logging.INFO)
server = ('175.6.5.153', 7709)

print(f"Testing server {server} via GOST 12345...")
try:
    client = Quotes.factory(market='std', bestip=False, server=server, timeout=10)
    data = client.transactions(symbol='000001', date='20260109')
    if data is not None and not data.empty:
        print(f"SUCCESS: Retrieved {len(data)} rows")
    else:
        print("FAILED: Empty data")
except Exception as e:
    print(f"ERROR: {e}")


from mootdx.quotes import Quotes
import sys

def test():
    ip = '175.6.5.153'
    port = 7709
    print(f"Testing {ip}:{port}...")
    try:
        c = Quotes.factory(market='std', bestip=False, server=(ip, port), timeout=10)
        d = c.transactions(symbol='000001', date='20260109')
        if d is not None and not d.empty:
            print(f"SUCCESS: Received {len(d)} rows")
        else:
            print("FAILED: Data is empty or None")
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    test()

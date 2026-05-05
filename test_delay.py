
import time
import sys
from mootdx.quotes import Quotes

STOCKS = ['000333', '000538', '000895', '002001', '002049', '002179']
SERVER = ('59.36.5.11', 7709)

def test_delay(delay=1.0):
    print(f"Testing with {delay}s delay...")
    client = Quotes.factory(market='std', bestip=False, server=SERVER)
    
    success = 0
    for symbol in STOCKS:
        print(f"Fetching {symbol}...", end=" ", flush=True)
        try:
            data = client.transactions(symbol=symbol, date='20260109')
            if data is not None and not data.empty:
                print(f"✅ ({len(data)})")
                success += 1
            else:
                print("❌ No Data")
        except Exception as e:
            print(f"❌ Error: {e}")
            
        time.sleep(delay)
        
    print(f"Result: {success}/{len(STOCKS)}")

if __name__ == "__main__":
    test_delay(1.5)

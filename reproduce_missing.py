
import sys
from mootdx.quotes import Quotes

SERVERS = [
    # Proven Good
    ('59.36.5.11', 7709), 
    
    # New Candidates
    ('180.153.18.170', 7709),
    ('180.153.18.171', 7709),
    ('119.147.212.82', 7709),
    ('121.14.104.22', 7709),
    ('202.108.23.105', 7709),
    ('115.238.56.198', 7709),
    ('60.191.117.167', 7709),
    ('218.75.126.9', 7709),
    ('115.238.90.165', 7709),
    ('124.160.88.183', 7709),
    ('61.152.107.141', 7709),
]

def test_servers(symbol):
    print(f"\n=== Testing {symbol} against all servers ===")
    
    for ip, port in SERVERS:
        print(f"Testing {ip}:{port}...", end=" ", flush=True)
        try:
            client = Quotes.factory(market='std', bestip=False, server=(ip, port))
            data = client.transactions(symbol=symbol, date='20260109')
            
            if data is not None and not data.empty:
                print(f"✅ SUCCESS ({len(data)} rows)")
            else:
                print("❌ FAILED (No Data)")
        except Exception as e:
            print(f"❌ ERROR ({e})")

if __name__ == "__main__":
    # Test stocks that failed even with concurrency=1
    test_servers("000333") 
    test_servers("000538")
    test_servers("000895")

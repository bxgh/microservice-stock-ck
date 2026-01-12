from mootdx.quotes import Quotes
import time
from datetime import datetime
import pandas as pd

targets = [
    "175.6.5.153", "139.9.51.18", "139.159.239.163", "139.9.133.247",
    "139.9.133.153", "139.9.133.18", "139.9.51.163", "139.159.239.18",
    "116.205.163.254", "116.205.171.132", "116.205.183.150", 
    "121.36.217.200", "121.36.217.201", "121.36.217.202",
    "124.71.187.122", "119.147.212.81", "123.60.84.66",
    "121.14.75.24", "115.238.114.77", "115.238.24.23", "114.55.109.11"
]

def test_ticks(ip):
    now_str = datetime.now().strftime("%H:%M")
    print(f"Testing {ip:15} (Local Time: {now_str})")
    try:
        client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=3.0)
        # Test 000001 (Ping An Bank)
        df = client.transactions(symbol='000001', start=0, offset=5)
        if df is not None and not df.empty:
            latest_time = df.iloc[0]['time']
            latest_price = df.iloc[0]['price']
            is_realtime = latest_time >= "09:30" and latest_time <= now_str
            print(f"  -> Latest: {latest_time} | Price: {latest_price} | {'✅ REALTIME' if is_realtime else '❌ STALE'}")
            return is_realtime
        else:
            print("  -> No Transactions")
            return False
    except Exception as e:
        print(f"  -> Connection Error: {e}")
        return False

print("Scanning for real-time tick servers...")
realtime_ips = []
for ip in targets:
    if test_ticks(ip):
        realtime_ips.append(ip)
    time.sleep(0.5)

print("\nReal-time servers found:")
for ip in realtime_ips:
    print(f"- {ip}")

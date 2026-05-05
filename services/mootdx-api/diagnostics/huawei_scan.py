
import socket
import time
from mootdx.quotes import Quotes

def test_single(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((ip, 7709))
        sock.close()
        # Longer timeout for protocol
        client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=5.0)
        df = client.quotes(symbol=['000001'])
        if df is not None and not df.empty:
            return True, "OK"
    except Exception as e:
        return False, str(e)
    return False, "Unknown"

# Focused Huawei cloud scan
huawei_ips = [
    "124.71.85.110", "121.36.217.200", "121.36.217.201", "121.36.217.202",
    "116.205.163.254", "116.205.171.132", "116.205.183.150", 
    "139.9.133.247", "139.9.51.18", "139.159.239.163",
    "124.70.176.52", "124.70.199.56", "124.70.133.119", "124.70.75.113"
]

print("Testing refined Huawei Cloud IPs...")
for ip in huawei_ips:
    ok, msg = test_single(ip)
    if ok:
        print(f"✅ {ip}")
    else:
        # print(f"❌ {ip} | {msg}")
        pass
    time.sleep(1) # Slow enough to be "human-like"

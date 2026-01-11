
import socket
import time
from mootdx.quotes import Quotes

def test_single(ip):
    start = time.time()
    try:
        # Socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((ip, 7709))
        sock.close()
        
        # Protocol
        try:
            client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=3.0)
            client.get_security_count(0)
            return True, (time.time() - start)*1000
        except Exception as e:
            return False, str(e)
    except Exception as e:
        return False, str(e)

targets = [
    "175.6.5.153", "139.9.51.18", "139.159.239.163", # Known Good
    "119.147.212.81", "124.71.187.122",              # Known Bad in current setup
    "139.9.133.247", "139.9.133.248", "139.9.133.249",
    "121.14.110.210", "121.14.110.200", "113.105.142.136",
    "121.36.225.169", "124.70.133.119",
    "47.107.64.168", "123.60.84.66", "59.36.5.11"
]

print("Starting serial test (to avoid firewall issues)...")
for ip in targets:
    ok, val = test_single(ip)
    if ok:
        print(f"✅ {ip:15} | {val:7.2f}ms")
    else:
        print(f"❌ {ip:15} | {val}")
    time.sleep(0.5) # Be gentle

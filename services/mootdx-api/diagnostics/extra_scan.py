
import socket
import time
from mootdx.quotes import Quotes

def test_single(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect((ip, 7709))
        sock.close()
        client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=1.5)
        df = client.quotes(symbol=['000001'])
        if df is not None and not df.empty:
            return True
    except:
        pass
    return False

# 扩大范围搜索
candidates = [
    "180.153.18.170", "180.153.18.171", "180.153.18.172",
    "61.152.249.2", "61.152.174.197", "114.80.63.12", "114.80.63.35",
    "119.29.19.242", "119.29.20.1", "119.29.21.1",
    "121.36.225.169", "121.36.54.217", "121.36.81.195",
    "111.41.147.114", "111.154.219.110"
]

print("Scanning candidates...")
working = []
for ip in candidates:
    if test_single(ip):
        print(f"✅ {ip}")
        working.append(ip)
    else:
        # print(f"❌ {ip}")
        pass

print("\nAll Working found in this session:")
print(", ".join(working))

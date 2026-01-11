
import socket
from mootdx.quotes import Quotes

def test(ip):
    try:
        client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=2.0)
        if not client.quotes(['000001']).empty: return True
    except: pass
    return False

ips = ["121.14.110.210", "113.105.142.136", "121.14.110.200", # ZSZQ
       "115.238.90.165", "60.191.117.167", # HTSZ
       "119.29.19.242", "183.57.72.15", # GFSZ
       "218.16.123.46", "114.80.149.32"] # CITIC/AX

for ip in ips:
    if test(ip): print(f"✅ {ip}")

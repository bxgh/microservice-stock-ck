
import socket
import time
from mootdx.quotes import Quotes

def test_single(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        sock.connect((ip, 7709))
        sock.close()
        return True
    except:
        return False

print("Scanning 175.6.5.0/24 for raw TCP...")
working_tcp = []
for i in range(1, 255):
    ip = f"175.6.5.{i}"
    if test_single(ip):
        working_tcp.append(ip)

print(f"Found {len(working_tcp)} reachable IPs.")
for ip in working_tcp:
    try:
        client = Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=2.0)
        df = client.quotes(symbol=['000001'])
        if not df.empty:
            print(f"✅ Protocol Success: {ip}")
    except:
        pass

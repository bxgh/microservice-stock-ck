from mootdx.quotes import factory
import pandas as pd
from datetime import datetime

codes = ['000001', '600519', '000725']

def test_server(ip, port):
    print(f"\nTesting server: {ip}:{port}")
    try:
        client = factory.get_h_client(host=ip, port=port, timeout=5)
        for code in codes:
            # Test getting today's ticks (no date)
            df = client.transactions(symbol=code, start=0, offset=10)
            if df is not None and not df.empty:
                print(f"  {code}: Latest Tick Time: {df.iloc[0]['time']}, Price: {df.iloc[0]['price']}")
            else:
                print(f"  {code}: No data")
    except Exception as e:
        print(f"  Error: {e}")

# Get best IPs from mootdx
try:
    from mootdx.server import Server
    server = Server()
    best_ips = server.best_ip()
    print("Best IPs from mootdx:")
    for item in best_ips[:5]:
        print(f"  {item['name']} - {item['ip']}:{item['port']} (Time: {item['time']}ms)")
        test_server(item['ip'], item['port'])
except Exception as e:
    print(f"Could not get best IPs: {e}")

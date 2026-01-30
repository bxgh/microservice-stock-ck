
import asyncio
import socket
import time
import os
import sys

# --- Monkey Patch: Force Source IP for TDX ---
_TD_BIND_IP = os.getenv("TDX_BIND_IP", "192.168.151.111")
_OriginalSocket = socket.socket
class _BoundSocket(_OriginalSocket):
    def connect(self, address):
        is_tdx = isinstance(address, tuple) and len(address) >= 2 and address[1] in [7701, 7709, 7711, 7727]
        if is_tdx:
            try: self.bind((_TD_BIND_IP, 0))
            except: pass
        super().connect(address)
socket.socket = _BoundSocket
# --- End Patch ---

from mootdx.quotes import Quotes

MOOTDX_HQ = [
    '110.41.147.114', '8.129.13.54', '120.24.149.49', '47.113.94.204', '8.129.174.169', '110.41.154.219',
    '124.70.176.52', '47.100.236.28', '101.133.214.242', '47.116.21.80', '47.116.105.28', '124.70.199.56',
    '121.36.54.217', '121.36.81.195', '123.249.15.60', '124.71.85.110', '139.9.51.18', '139.159.239.163',
    '106.14.201.131', '106.14.190.242', '121.36.225.169', '123.60.70.228', '123.60.73.44', '124.70.133.119',
    '124.71.187.72', '124.71.187.122', '119.97.185.59', '47.107.64.168', '124.70.75.113', '124.71.9.153',
    '123.60.84.66', '120.46.186.223', '124.70.22.210', '139.9.133.247', '116.205.163.254', '116.205.171.132',
    '116.205.183.150'
]

TDXPY_HQ = [
    '218.85.139.19', '218.85.139.20', '58.23.131.163', '218.6.170.47', '123.125.108.14', '180.153.18.170',
    '180.153.18.171', '180.153.18.172', '202.108.253.130', '202.108.253.131', '202.108.253.139', '60.191.117.167',
    '115.238.56.198', '218.75.126.9', '115.238.90.165', '124.160.88.183', '60.12.136.250', '218.108.98.244',
    '218.108.47.69', '223.94.89.115', '218.57.11.101', '58.58.33.123', '14.17.75.71', '114.80.63.12',
    '114.80.63.35', '180.153.39.51', '119.147.212.81', '221.231.141.60', '101.227.73.20', '101.227.77.254',
    '14.215.128.18', '59.173.18.140', '60.28.23.80', '218.60.29.136', '122.192.35.44', '112.95.140.74',
    '112.95.140.92', '112.95.140.93', '114.80.149.19', '114.80.149.21', '114.80.149.22', '114.80.149.91',
    '114.80.149.92', '121.14.104.60', '121.14.104.66', '123.126.133.13', '123.126.133.14', '123.126.133.21',
    '211.139.150.61', '59.36.5.11', '119.29.19.242', '123.138.29.107', '123.138.29.108', '124.232.142.29',
    '183.57.72.11', '183.57.72.12', '183.57.72.13', '183.57.72.15', '183.57.72.21', '183.57.72.22',
    '183.57.72.23', '183.57.72.24', '183.60.224.177', '183.60.224.178', '113.105.92.100', '113.105.92.101',
    '113.105.92.102', '113.105.92.103', '113.105.92.104', '113.105.92.99', '117.34.114.13', '117.34.114.14',
    '117.34.114.15', '117.34.114.16', '117.34.114.17', '117.34.114.18', '117.34.114.20', '117.34.114.27',
    '117.34.114.30', '117.34.114.31', '182.131.3.252', '183.60.224.11', '58.210.106.91', '58.63.254.216',
    '58.63.254.219', '58.63.254.247', '123.125.108.90', '175.6.5.153', '182.118.47.151', '182.131.3.245',
    '202.100.166.27', '222.161.249.156', '42.123.69.62', '58.63.254.191', '58.63.254.217', '120.55.172.97',
    '139.217.20.27', '202.100.166.21', '202.96.138.90', '218.106.92.182', '218.106.92.183', '220.178.55.71',
    '220.178.55.86'
]

ALL_IPS = sorted(list(set(MOOTDX_HQ + TDXPY_HQ)))

async def test_protocol(ip, port):
    loop = asyncio.get_event_loop()
    start = time.time()
    try:
        # Step 1: Protocol Handshake
        # We use the monkey-patched socket automatically
        client = await loop.run_in_executor(
            None,
            lambda: Quotes.factory(market='std', server=(ip, int(port)), bestip=False, timeout=2.0)
        )
        
        # Test a real command (Transaction)
        # client.transaction(symbol, start, offset)
        # We use a common stock like sz000001
        data = await loop.run_in_executor(None, lambda: client.transaction(symbol='sz000001', start=0, offset=1))
        
        latency = (time.time() - start) * 1000
        # data is DataFrame when successful
        if data is not None and not data.empty:
            return True, latency, f"OK ({len(data)} Ticks)"
        return False, 0, "No data (Empty DataFrame)"
    except Exception as e:
        return False, 0, str(e)

async def scan():
    print(f"🚀 Mass Scanning {len(ALL_IPS)} TDX Servers (Bind: {_TD_BIND_IP})...\n")
    
    tasks = []
    sem = asyncio.Semaphore(15)
    
    async def worker(ip):
        async with sem:
            ok, lat, msg = await test_protocol(ip, 7709)
            if ok:
                print(f"  [FOUND] {ip:15} | {lat:7.2f}ms")
            return ok, lat, msg, ip
            
    for ip in ALL_IPS:
        tasks.append(worker(ip))
        
    results = await asyncio.gather(*tasks)
    
    success = [(r[3], r[1], r[2]) for r in results if r[0]]
    success.sort(key=lambda x: x[1])
    
    print("\n" + "="*70)
    print(f"{'RANK':4} | {'IP':15} | {'LATENCY':10} | {'MSG'}")
    print("-" * 70)
    for idx, (ip, lat, msg) in enumerate(success):
        print(f"#{idx+1:02}  | {ip:15} | {lat:7.2f}ms | {msg}")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(scan())

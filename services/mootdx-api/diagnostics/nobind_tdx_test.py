
import asyncio
import socket
import time
import os
import pandas as pd
from mootdx.quotes import Quotes

# 广泛的通达信服务器列表
EXTENDED_SERVERS = [
    "119.147.212.81:7709", "124.71.187.122:7709", "175.6.5.153:7709", "139.9.51.18:7709",
    "139.159.239.163:7709", "47.107.64.168:7709", "119.29.19.242:7709", "123.60.84.66:7709",
    "59.36.5.11:7709", "115.238.90.165:7709", "124.160.88.183:7709", "60.191.117.167:7709",
    "180.153.18.170:7709", "180.153.18.171:7709", "180.153.18.172:7709", "218.16.123.46:7709",
    "218.75.126.9:7709", "218.108.47.69:7709", "218.108.98.244:7709", "14.215.128.18:7709",
    "59.175.238.38:7709", "113.105.142.136:7709", "121.14.110.210:7709", "121.14.2.7:7709",
    "221.231.141.60:7709", "101.227.73.20:7709", "101.227.77.20:7709", "114.80.149.32:7709",
    "114.80.149.84:7709", "124.70.190.222:7709", "124.70.1.180:7709", "119.3.179.6:7709"
]

async def test_tdx_protocol(ip, port):
    loop = asyncio.get_event_loop()
    start = time.time()
    try:
        # No bind here, use default interface
        client = await loop.run_in_executor(
            None,
            lambda: Quotes.factory(market='std', server=(ip, int(port)), bestip=False, timeout=2)
        )
        data = await loop.run_in_executor(None, lambda: client.stocks(market=0))
        latency = (time.time() - start) * 1000
        if data is not None and not data.empty:
            return True, latency, "OK"
        return True, latency, "Empty"
    except Exception as e:
        return False, 0, str(e)

async def run():
    print(f"🔍 TDX Connectivity Diagnostic (NO BINDING - Using Default Interface)")
    all_targets = list(set(EXTENDED_SERVERS))
    results = []
    chunk_size = 5
    for i in range(0, len(all_targets), chunk_size):
        chunk = all_targets[i:i+chunk_size]
        tasks = [test_tdx_protocol(s.split(":")[0], s.split(":")[1]) for s in chunk]
        chunk_results = await asyncio.gather(*tasks)
        for host, (ok, lat, msg) in zip(chunk, chunk_results):
            if ok:
                results.append((host, lat, msg))
                print(f"  ✅ {host:22} | {lat:7.2f}ms")
    
    results.sort(key=lambda x: x[1])
    print("\n🚀 Top 10 IPs (No Binding):")
    print(",".join([x[0] for x in results[:10]]))

if __name__ == "__main__":
    asyncio.run(run())

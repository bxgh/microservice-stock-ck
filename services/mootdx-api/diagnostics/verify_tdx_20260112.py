
import asyncio
import time
from mootdx.quotes import Quotes

# List from VERIFIED_TDX_HOSTS_20260111.md
TARGET_IPS = [
    # Haitong Cluster
    "175.6.5.131", "175.6.5.136", "175.6.5.138", "175.6.5.144", 
    "175.6.5.146", "175.6.5.150", "175.6.5.151", "175.6.5.153", 
    "175.6.5.154", "175.6.5.155", "175.6.5.156", "175.6.5.157", 
    "175.6.5.158",
    # Huawei Cloud Cluster
    "139.9.133.247", "139.9.51.18", "139.159.239.163"
]

async def verify_ip(ip):
    loop = asyncio.get_event_loop()
    start = time.time()
    try:
        # We run the synchronous mootdx call in an executor
        client = await loop.run_in_executor(
            None, 
            lambda: Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=2.0)
        )
        
        # Test fetching data (Ping logic isn't enough, we need a real query)
        # Using get_security_count or similar lightweight query if possible.
        # But factory() already does a connect. Let's try getting one quote.
        res = await loop.run_in_executor(
            None,
            lambda: client.quotes(symbol=['000001'])
        )
        
        latency = (time.time() - start) * 1000
        if not res.empty:
            return True, latency, "OK"
        else:
            return False, 0, "Empty Data"
    except Exception as e:
        return False, 0, str(e)

async def main():
    print(f"🔍 Verifying {len(TARGET_IPS)} TDX Hosts... (Date: 2026-01-12)")
    print("-" * 60)
    print(f"{'IP Address':<16} | {'Status':<8} | {'Latency':<10} | {'Note'}")
    print("-" * 60)
    
    tasks = [verify_ip(ip) for ip in TARGET_IPS]
    results = await asyncio.gather(*tasks)
    
    working_count = 0
    for ip, (ok, lat, msg) in zip(TARGET_IPS, results):
        status_icon = "✅" if ok else "❌"
        lat_str = f"{lat:.1f}ms" if ok else "-"
        print(f"{ip:<16} | {status_icon:<8} | {lat_str:<10} | {msg}")
        if ok: working_count += 1
            
    print("-" * 60)
    print(f"Summary: {working_count}/{len(TARGET_IPS)} hosts are fully operational.")

if __name__ == "__main__":
    asyncio.run(main())

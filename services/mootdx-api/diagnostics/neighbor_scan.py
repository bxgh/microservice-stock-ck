
import asyncio
import socket
import time
import os

async def check_port(ip, port, timeout=0.1):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

async def scan_subnet(subnet_prefix, port=7709):
    tasks = []
    for i in range(1, 255):
        ip = f"{subnet_prefix}.{i}"
        tasks.append(check_port(ip, port))
    
    results = await asyncio.gather(*tasks)
    return [f"{subnet_prefix}.{i}" for i, ok in enumerate(results, 1) if ok]

async def protocol_test(ip):
    from mootdx.quotes import Quotes
    loop = asyncio.get_event_loop()
    try:
        client = await loop.run_in_executor(
            None, 
            lambda: Quotes.factory(market='std', server=(ip, 7709), bestip=False, timeout=1.5)
        )
        df = client.quotes(symbol=['000001'])
        if not df.empty:
            return True
    except:
        pass
    return False

async def main():
    subnets = [
        "139.9.51", "139.9.133", "139.159.239", 
        "139.9.11", "139.9.135", "139.9.129",
        "116.205.163", "116.205.171", "116.205.183",
        "124.70.176", "124.70.199", "124.70.133", "124.70.75", "124.70.22",
        "124.71.85", "124.71.187", "124.71.9", "175.6.5"
    ]
    
    all_alive = []
    print(f"Starting raw TCP scan on {len(subnets)} subnets...")
    for sn in subnets:
        start = time.time()
        alive = await scan_subnet(sn)
        if alive:
            print(f"Subnet {sn}.0/24: found {len(alive)} IPs with port 7709 open.")
            all_alive.extend(alive)
            
    if not all_alive:
        print("No IPs found with port 7709 open.")
        return

    print(f"\nVerifying TDX protocol for {len(all_alive)} candidates...")
    working = []
    sem = asyncio.Semaphore(10)
    
    async def task_with_sem(ip):
        async with sem:
            if await protocol_test(ip):
                return ip
            return None

    results = await asyncio.gather(*[task_with_sem(ip) for ip in all_alive])
    working = [r for r in results if r]

    print("\n--- NEW WORKING TDX NODES ---")
    if working:
        for ip in working:
            print(f"✅ {ip}:7709")
        print("\nRecommended update for TDX_HOSTS:")
        print(",".join([f"{ip}:7709" for ip in working]))
    else:
        print("No new working nodes found.")

if __name__ == "__main__":
    asyncio.run(main())

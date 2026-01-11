
import asyncio
import socket
import time

async def test_protocol(ip, port):
    loop = asyncio.get_event_loop()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        sock.connect((ip, int(port)))
        sock.close()
        
        from mootdx.quotes import Quotes
        client = await loop.run_in_executor(
            None, 
            lambda: Quotes.factory(market='std', server=(ip, int(port)), bestip=False, timeout=1.0)
        )
        return True
    except:
        return False

async def subnet_scan(prefix):
    print(f"Scanning {prefix}.0/24...")
    tasks = []
    for i in range(1, 255):
        tasks.append(test_protocol(f"{prefix}.{i}", 7709))
    
    results = await asyncio.gather(*tasks)
    working = [f"{prefix}.{i}" for i, ok in enumerate(results, 1) if ok]
    return working

async def run():
    # We found working ones in these ranges
    found = []
    for prefix in ["139.9.51", "139.9.133", "139.159.239", "175.6.5"]:
        res = await subnet_scan(prefix)
        found.extend(res)
        if res:
            print(f"  Found in {prefix}: {res}")
            
    print("\n--- Final Working List ---")
    print(", ".join(found))

if __name__ == "__main__":
    asyncio.run(run())

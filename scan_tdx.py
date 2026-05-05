
import asyncio
import json
import socket

async def check_server(name, ip, port, timeout=3):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        print(f"SUCCESS: {name} ({ip}:{port}) is REACHABLE")
        return (ip, port, True)
    except Exception as e:
        print(f"FAIL: {name} ({ip}:{port}) - {e}")
        return (ip, port, False)

async def main():
    with open('tdx_hosts_clean.json', 'r') as f:
        data = json.load(f)
    
    tasks = []
    print(f"Scanning {len(data['TDX'])} servers...")
    for item in data['TDX']:
        # item structure: [name, ip, port]
        name, ip, port = item
        tasks.append(check_server(name, ip, port))
    
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for _, _, success in results if success)
    print(f"\nScan Complete. Reachable Servers: {success_count}/{len(data['TDX'])}")

if __name__ == "__main__":
    asyncio.run(main())

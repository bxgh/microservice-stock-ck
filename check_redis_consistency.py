
import asyncio
import redis.asyncio as redis

SERVERS = [
    {'name': '41', 'host': '192.168.151.41'},
    {'name': '58', 'host': '192.168.151.58'},
    {'name': '111', 'host': '192.168.151.111'}
]

async def check(server):
    host = server['host']
    print(f"\nChecking Redis on {host}...")
    try:
        r = redis.from_url(f"redis://{host}:6379/0", password="redis123", decode_responses=True, socket_timeout=3)
        count = await r.scard("metadata:stock_codes")
        print(f"[{server['name']}] DB 0 Count: {count}")
        
        # Check DB 1
        await r.select(1)
        count1 = await r.scard("metadata:stock_codes")
        print(f"[{server['name']}] DB 1 Count: {count1}")
        
        await r.aclose()
        return count
    except Exception as e:
        print(f"[{server['name']}] Error: {e}")
        return -1

async def main():
    tasks = [check(s) for s in SERVERS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

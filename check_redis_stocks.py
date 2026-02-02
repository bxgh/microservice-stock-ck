
import asyncio
import redis.asyncio as redis
import os

async def main():
    # Attempt to connect to one of the nodes
    redis_host = '192.168.151.41'
    redis_password = 'redis123'
    
    print(f"Connecting to Redis at {redis_host}...")
    r = redis.from_url(f"redis://{redis_host}:6379/1", password=redis_password, decode_responses=True)
    # Note: DB 1 is used in .env, so let's try DB 1. But verify_redis_stocks.py didn't specify DB, defaulting to 0. 
    # Let's check both or just DB 1 if that's where config is?
    # TickSyncService uses REDIS_DB=1 in .env (Step 16).
    
    try:
        await r.ping()
        print("Connected.")
        
        # Check DB 1 (Config)
        total_db1 = await r.scard("metadata:stock_codes")
        print(f"Total stocks in Redis (DB 1) 'metadata:stock_codes': {total_db1}")

        if total_db1 == 0:
             # Try DB 0
             print("DB 1 empty, checking DB 0...")
             await r.select(0)
             total_db0 = await r.scard("metadata:stock_codes")
             print(f"Total stocks in Redis (DB 0) 'metadata:stock_codes': {total_db0}")
             
             # Also check if keys exist with other names
             keys = await r.keys("metadata:*")
             print(f"Keys in metadata namespace: {len(keys)}")

        # Shards
        shard0 = await r.scard("metadata:stock_codes:shard:0")
        shard1 = await r.scard("metadata:stock_codes:shard:1")
        shard2 = await r.scard("metadata:stock_codes:shard:2")
        print(f"Shards count: S0={shard0}, S1={shard1}, S2={shard2}")
        print(f"Sum of shards: {shard0 + shard1 + shard2}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await r.aclose()

if __name__ == "__main__":
    asyncio.run(main())

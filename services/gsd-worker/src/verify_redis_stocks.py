
import asyncio
import redis.asyncio as redis
import os

async def main():
    redis_host = os.getenv("REDIS_HOST", "node-41-redis")
    redis_password = os.getenv("REDIS_PASSWORD", "redis123")
    
    r = redis.from_url(f"redis://{redis_host}:6379", password=redis_password, decode_responses=True)
    
    try:
        print("Checking Redis stock list...")
        
        # 1. 检查全量总数
        total = await r.scard("metadata:stock_codes")
        print(f"Total stocks in Redis: {total}")
        
        # 2. 检查分片总数
        shard0 = await r.scard("metadata:stock_codes:shard:0")
        shard1 = await r.scard("metadata:stock_codes:shard:1")
        shard2 = await r.scard("metadata:stock_codes:shard:2")
        print(f"Shards count: S0={shard0}, S1={shard1}, S2={shard2}")
        print(f"Sum of shards: {shard0 + shard1 + shard2}")
        
        # 3. 检查特定无效代码
        invalid_codes = ['000005.SZ', '000013.SZ', '000005', '000013']
        for code in invalid_codes:
            is_member = await r.sismember("metadata:stock_codes", code)
            print(f"Is {code} in Redis? {is_member}")
            
        # 4. 随机抽查一些代码的前缀
        samples = await r.srandmember("metadata:stock_codes", 20)
        print("\nRandom 20 samples from Redis:")
        for s in samples:
            print(f"  {s}")
            
    finally:
        await r.aclose()

if __name__ == "__main__":
    asyncio.run(main())

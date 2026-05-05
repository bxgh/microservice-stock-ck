import asyncio
import os
import sys
import time
import logging

# Setup paths
sys.path.insert(0, '/app/src')
sys.path.insert(0, '/app/libs/gsd-shared')

from gsd_shared.redis_protocol import RedisStreamClient, TickJob, JobType

logging.basicConfig(level=logging.INFO)

async def main():
    # Explicitly NO PASSWORD for benchmark
    redis_host = "127.0.0.1"
    redis_port = 16379
    is_cluster = True
    redis_url = f"redis://{redis_host}:{redis_port}/0"
    
    print(f"Starting Performance Benchmark on {redis_url}...")
    
    # We provide a dummy list of 1000 stocks
    stocks = [f"{i:06d}" for i in range(1, 1001)]
    rows = [{"code": s, "market": "sz"} for s in stocks]
    
    client = RedisStreamClient(redis_url, is_cluster=is_cluster)
    
    start_t = time.time()
    count = 0
    import uuid
    
    for row in rows:
        job = TickJob(
            job_id=str(uuid.uuid4()),
            stock_code=row['code'],
            type=JobType.POST_MARKET,
            date="20260112",
            market=row['market']
        )
        await client.publish_job(job)
        count += 1
        if count % 200 == 0:
            print(f"  Published {count}...")
            
    print(f"Benchmark: Published {count} jobs in {time.time() - start_t:.2f}s")
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
EOF

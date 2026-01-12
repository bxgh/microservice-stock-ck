
import sys
import os
import uuid
import asyncio

# Setup path
sys.path.insert(0, '/app/libs/gsd-shared')

from gsd_shared.redis_protocol import RedisStreamClient, TickJob, JobType

async def main():
    redis_url = "redis://127.0.0.1:16379"
    client = RedisStreamClient(redis_url, is_cluster=True)
    
    stocks = ["000001", "600519", "000002", "601318", "000725"]
    date_str = "20260112"
    
    print(f"Publishing {len(stocks)} jobs to {redis_url}...")
    for code in stocks:
        job = TickJob(
            job_id=str(uuid.uuid4()),
            stock_code=code,
            type=JobType.POST_MARKET,
            date=date_str
        )
        await client.publish_job(job)
        print(f"  Published {code}")
    
    await client.aclose()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())

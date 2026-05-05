import asyncio
import os
import uuid
import sys

# Add shared lib path for direct execution
sys.path.append("/app/libs/gsd-shared")

from gsd_shared.redis_protocol import RedisStreamClient, TickJob, JobType

async def main():
    # Hardcoded values for the node-41 environment
    redis_host = "127.0.0.1"
    redis_port = 16379
    is_cluster = True
    redis_url = f"redis://{redis_host}:{redis_port}/0"
    
    print(f"Connecting to {redis_url} (Cluster: {is_cluster})")
    client = RedisStreamClient(redis_url, is_cluster=is_cluster)
    
    # Publish 20 jobs to keep it busy
    stocks = ["000001", "000002", "600519", "601318", "000725"] * 4
    for i, code in enumerate(stocks):
        job = TickJob(
            job_id=str(uuid.uuid4()),
            stock_code=code,
            type=JobType.POST_MARKET,
            date="20260112"
        )
        await client.publish_job(job)
        print(f"Published {code}")
    await client.aclose()
    print("Done publishing.")

if __name__ == "__main__":
    asyncio.run(main())

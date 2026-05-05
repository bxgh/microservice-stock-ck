
import asyncio
import logging
import argparse
import sys
import os
from datetime import datetime

# Append shared path: /app/libs/gsd-shared
# gsd-worker Dockerfile sets PYTHONPATH=/app/src, but shared lib is in /app/libs
# Use insert(0) to prioritize local volume over installed package
sys.path.insert(0, "/app/libs/gsd-shared")

from src.core.stream_adapter import JobPublisher, BatchWriter
from gsd_shared.redis_protocol import JobType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("stream-tick-runner")

async def run_publisher(args):
    pub = JobPublisher()
    date_str = args.date
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")
        
    logger.info(f"Running Publisher for date {date_str}...")
    await pub.publish_daily_jobs(date_str, JobType(args.job_type))

async def run_consumer(args):
    logger.info("Running Consumer (BatchWriter)...")
    consumer = BatchWriter()
    await consumer.start()

def main():
    parser = argparse.ArgumentParser(description="Redis Stream Tick Worker")
    parser.add_argument("mode", choices=["publisher", "consumer"], help="Run mode: publisher or consumer")
    parser.add_argument("--date", help="Date YYYYMMDD (default: today)")
    parser.add_argument("--job-type", default="post_market", choices=["post_market", "intraday"], help="Job Type")
    
    args = parser.parse_args()
    
    try:
        loop = asyncio.get_event_loop()
        if args.mode == "publisher":
            loop.run_until_complete(run_publisher(args))
        elif args.mode == "consumer":
            loop.run_until_complete(run_consumer(args))
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

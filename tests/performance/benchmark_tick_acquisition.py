
import asyncio
import argparse
import logging
import sys
import os
import time
from datetime import datetime
import asynch
import redis.asyncio as redis

# Add project root to path
sys.path.append(os.getcwd())
from core.tick_sync_service import TickSyncService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("benchmark")

async def clear_clickhouse_data(date_str):
    """Clear tick data for the specified date"""
    logger.info(f"Cleaning ClickHouse data for {date_str}...")
    try:
        conn = await asynch.connect(
            host=os.getenv("CLICKHOUSE_HOST", "127.0.0.1"),
            port=9000,
            database="stock_data",
            user=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", "")
        )
        async with conn.cursor() as cursor:
            # Drop partition is faster and cleaner for full resets
            # Convert YYYYMMDD to YYYY-MM-DD
            dt = datetime.strptime(date_str, "%Y%m%d")
            fmt_date = dt.strftime("%Y-%m-%d")
            
            # ALTER TABLE on Distributed is not supported, must run on local table
            # Assuming 'tick_data_local' is the ReplicatedMergeTree table
            await cursor.execute(f"ALTER TABLE tick_data_local DELETE WHERE trade_date = '{fmt_date}'")
        logger.info("✓ DB Cleaned (tick_data_local)")
    except Exception as e:
        logger.error(f"Failed to clear DB: {e}")
        # Don't exit, might be empty

async def get_stocks_from_redis(shard_index=0):
    """Get stocks directly from Redis for the specified shard"""
    logger.info(f"Fetching stocks for Shard {shard_index} from Redis...")
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", '127.0.0.1'), 
            port=6379, 
            password=os.getenv("REDIS_PASSWORD", 'redis123'),
            decode_responses=True
        )
        # Try metadata:stock_codes:shard:0
        key = f"metadata:stock_codes:shard:{shard_index}"
        stocks = await r.smembers(key)
        await r.close()
        
        if stocks:
             # Clean codes (remove suffix if any)
            clean = sorted([s.split('.')[0] for s in stocks])
            logger.info(f"✓ Found {len(clean)} stocks in Redis Shard {shard_index}")
            return clean
        else:
            logger.warning(f"Redis key {key} is empty!")
            return []
    except Exception as e:
        logger.error(f"Redis fetch failed: {e}")
        return []

async def fetch_all_stocks_from_api(shard_index=0):
    """Fallback: Fetch all stocks from API and simulate sharding"""
    logger.info("Fallback: Fetching ALL stocks from Mootdx API...")
    try:
        service = TickSyncService()
        await service.initialize()
        all_stocks = await service.get_all_stocks()
        await service.close()
        
        # User requested to test ALL stocks
        try:
            # Simple modulo to mimic sharding
            filtered = [s for s in all_stocks if int(s) % 3 == shard_index]
            logger.info(f"✓ Selected {len(filtered)} stocks for full benchmark (Shard {shard_index})")
            return filtered
        except Exception:
            return all_stocks
    except Exception as e:
        logger.error(f"API fetch failed: {e}")
        return []

async def main():
    parser = argparse.ArgumentParser(description="Tick Data Benchmark")
    parser.add_argument("--date", type=str, default="20260105", help="Date to fetch YYYYMMDD")
    parser.add_argument("--concurrency", type=int, default=6, help="Worker concurrency")
    parser.add_argument("--shard", type=int, default=0, help="Shard index")
    args = parser.parse_args()

    # 1. Clear DB
    await clear_clickhouse_data(args.date)

    # 2. Get Stocks
    stocks = await get_stocks_from_redis(args.shard)
    if not stocks:
        logger.info("Redis empty. Attempting to fetch full list from API as fallback...")
        stocks = await fetch_all_stocks_from_api(args.shard)
        
    if not stocks:
        logger.info("API failed. Falling back to CONFIG scope (HS300 + defaults)")
        # Initialize service to use its fallback
        service = TickSyncService()
        stocks = await service.get_stock_pool()
        # Mock sharding for fallback
        stocks = [s for s in stocks if int(s) % 3 == args.shard] # Simple hash for fallback
        logger.info(f"Fallback: {len(stocks)} stocks for Shard {args.shard}")

    if not stocks:
        logger.error("No stocks to process!")
        return

    # 3. Run Benchmark
    logger.info(f"Starting Benchmark: Date={args.date}, Stocks={len(stocks)}, Concurrency={args.concurrency}")
    
    start_time = time.time()
    
    service = TickSyncService()
    await service.initialize()
    
    try:
        results = await service.sync_stocks(
            stock_codes=stocks,
            trade_date=args.date,
            concurrency=args.concurrency
        )
        
        duration = time.time() - start_time
        total = results['total_records']
        success = results['success']
        
        logger.info("="*50)
        logger.info(f"BENCHMARK RESULTS")
        logger.info("="*50)
        logger.info(f"Duration:       {duration:.2f} seconds")
        logger.info(f"Stocks Fetched: {success} / {len(stocks)}")
        logger.info(f"Total Records:  {total:,}")
        logger.info(f"Throughput:     {total / duration:.2f} records/sec")
        logger.info(f"Avg Time/Stock: {duration / success if success else 0:.2f} seconds")
        if results.get('errors'):
            logger.info("="*50)
            logger.info(f"TOP 10 ERRORS")
            for err in results['errors'][:10]:
                logger.error(err)

        logger.info("="*50)
        
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())

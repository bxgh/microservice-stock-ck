
import argparse
import os
import sys
from redis.cluster import RedisCluster
from clickhouse_driver import Client

# Config
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis123")
REDIS_CLUSTER = os.getenv("REDIS_CLUSTER", "false").lower() == "true"

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "127.0.0.1")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", 9000))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "stock_data")

def get_redis_client():
    from redis import Redis
    from redis.cluster import RedisCluster
    auth_kwargs = {"password": REDIS_PASSWORD} if REDIS_PASSWORD else {}
    if REDIS_CLUSTER:
        return RedisCluster(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, **auth_kwargs)
    else:
        return Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, **auth_kwargs)

def get_clickhouse_client():
    return Client(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT, 
                  user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD, 
                  database=CLICKHOUSE_DB)

def clean_redis(dry_run=False):
    print(f"\n--- [1/2] Cleaning Redis Streams ---")
    keys = ["stream:tick:jobs", "stream:tick:data"]
    
    try:
        r = get_redis_client()
        for k in keys:
            exists = r.exists(k)
            if exists:
                if not dry_run:
                    r.delete(k)
                    print(f"✅ Deleted key: {k}")
                else:
                    print(f"⚠️  [DRY RUN] Would delete key: {k}")
            else:
                print(f"ℹ️  Key not found: {k}")
                
    except Exception as e:
        print(f"❌ Redis Error: {e}")

def clean_clickhouse(trade_date, dry_run=False):
    print(f"\n--- [2/2] Cleaning ClickHouse Data ({trade_date}) ---")
    formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
    
    try:
        client = get_clickhouse_client()
        # Fix: Target local table ON CLUSTER to ensure all shards delete data
        query = f"ALTER TABLE {CLICKHOUSE_DB}.tick_data_local ON CLUSTER stock_cluster DELETE WHERE trade_date = '{formatted_date}'"
        
        # Check count first (globally via Distributed table)
        count_sql = f"SELECT count(*) FROM {CLICKHOUSE_DB}.tick_data WHERE trade_date = '{formatted_date}'"
        count = client.execute(count_sql)[0][0]
        print(f"ℹ️  Found {count} rows for date {formatted_date}")
        
        if count > 0:
            if not dry_run:
                client.execute(query)
                print(f"✅ Executed: {query}")
                print("⏳ Note: ClickHouse deletes are asynchronous mutations. Data may take a moment to satisfy.")
            else:
                print(f"⚠️  [DRY RUN] Would execute: {query}")
        else:
            print("✅ No data to clean.")
            
    except Exception as e:
        print(f"❌ ClickHouse Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset Data Acquisition Environment")
    parser.add_argument("--date", type=str, required=True, help="Target trade date (e.g. 20260107)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without deleting")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    print(f"Target Date: {args.date}")
    print(f"Dry Run: {args.dry_run}")
    
    if not args.dry_run and not args.yes:
        confirm = input("\n⚠️  DANGER: This will delete ALL Redis Job Queues AND ClickHouse Data for this date. Continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
            
    clean_redis(args.dry_run)
    clean_clickhouse(args.date, args.dry_run)
    print("\n✅ Reset Complete.")

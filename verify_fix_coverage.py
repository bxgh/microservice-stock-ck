
import sys
import xxhash
from clickhouse_driver import Client

HOST = '192.168.151.111'
PORT = 9000
USER = 'admin'
PASSWORD = 'admin123'
DATABASE = 'stock_data'
DATE = '2026-02-02'

def normalize_code(code: str) -> str:
    code = str(code).strip()
    if '.' in code:
        parts = code.split('.')
        return parts[0] if len(parts[0]) == 6 else parts[-1]
    lower = code.lower()
    if lower.startswith(('sh', 'sz')):
        return code[2:]
    return code

try:
    print(f"Connecting to ClickHouse {HOST}...")
    client = Client(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE)
    
    # Check total stocks
    print(f"Fetching collected stocks for {DATE}...")
    rows = client.execute(f"SELECT DISTINCT stock_code FROM tick_data_intraday WHERE toDate(trade_date) = '{DATE}'")
    collected_codes = [normalize_code(r[0]) for r in rows]
    total_collected = len(collected_codes)
    print(f"Collected {total_collected} unique stocks.")
    
    # Check if total increased from ~3454
    if total_collected > 3500:
        print("✅ Stock count is increasing!")
    else:
        print("⚠️ Stock count stagnant (wait a bit or check logs).")

    # Shard breakdown
    shards = {0: 0, 1: 0, 2: 0}
    for code in collected_codes:
        digest = xxhash.xxh64(code).intdigest()
        shard_id = digest % 3
        shards[shard_id] += 1
        
    print("\nShard Coverage (xxHash % 3):")
    for s_id in range(3):
        count = shards.get(s_id, 0)
        print(f"Shard {s_id}: {count} stocks collected")

except Exception as e:
    print(f"ERROR: {e}")

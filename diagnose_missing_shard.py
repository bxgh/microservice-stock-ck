
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
    """标准化为 6 位纯数字"""
    code = str(code).strip()
    if '.' in code:
        parts = code.split('.')
        return parts[0] if len(parts[0]) == 6 else parts[-1]
    
    # 移除前缀
    lower = code.lower()
    if lower.startswith(('sh', 'sz')):
        return code[2:]
        
    return code

try:
    print(f"Connecting to ClickHouse {HOST}...")
    client = Client(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE)
    
    print(f"Fetching collected stocks for {DATE}...")
    rows = client.execute(f"SELECT DISTINCT stock_code FROM tick_data_intraday WHERE toDate(trade_date) = '{DATE}'")
    collected_codes = [normalize_code(r[0]) for r in rows]
    
    print(f"Collected {len(collected_codes)} unique stocks.")
    
    shards = {0: 0, 1: 0, 2: 0}
    
    for code in collected_codes:
        # Replicate StockUniverse logic: xxhash.xxh64(s).intdigest() % 3
        # Note: StockUniverse normalizes BEFORE hashing. 
        # _filter_and_normalize calls normalize_code, then sorts.
        # _shard_filter uses the normalized code.
        
        digest = xxhash.xxh64(code).intdigest()
        shard_id = digest % 3
        shards[shard_id] += 1
        
    print("\nShard Coverage (xxHash % 3):")
    for s_id in range(3):
        count = shards.get(s_id, 0)
        print(f"Shard {s_id}: {count} stocks collected")
        
    # Analyze
    total = sum(shards.values())
    if total > 0:
        for s_id in range(3):
            ratio = shards[s_id] / total
            print(f"Shard {s_id} Ratio: {ratio:.2%}")

    missing_shards = [s for s, c in shards.items() if c < 100] # threshold 100
    if missing_shards:
        print(f"\n❌ CONCLUSION: Shard {missing_shards} is MISSING!")
    else:
        print("\n✅ All shards seem to have data (but maybe partial?)")

except Exception as e:
    print(f"ERROR: {e}")

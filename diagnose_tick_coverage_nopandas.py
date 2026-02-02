
import sys
from clickhouse_driver import Client

# Config
HOST = '192.168.151.111' 
PORT = 9000
USER = 'admin'
PASSWORD = 'admin123'
DATABASE = 'stock_data'
DATE = '2026-02-02'

try:
    client = Client(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE)
    
    # 1. Get total distinct stocks collected today
    print(f"Querying distinct stocks collected on {DATE}...")
    collected_stocks = client.execute(f"""
        SELECT DISTINCT stock_code 
        FROM tick_data_intraday 
        WHERE toDate(trade_date) = '{DATE}'
    """)
    collected_set = set([s[0] for s in collected_stocks])
    collected_count = len(collected_set)
    print(f"Collected Stock Count: {collected_count}")

    # 2. Get total expected stocks
    # Using stock_adjust_factor as a proxy for all stocks
    ref_stocks = client.execute(f"""
        SELECT DISTINCT stock_code FROM stock_adjust_factor
    """)
    ref_set = set([s[0] for s in ref_stocks])
    ref_count = len(ref_set)
    print(f"Reference Stock Count (Total Market): {ref_count}")

    # 3. Calculate Missing
    missing_set = ref_set - collected_set
    missing_count = len(missing_set)
    
    print(f"\nMissing Stocks: {missing_count}")
    if ref_count > 0:
        print(f"Missing Ratio: {missing_count / ref_count:.2%}")
        
    # 4. Check Shard Distribution
    print("\nShard Distribution (cityHash64(stock_code) % 3):")
    
    dist_query = f"""
        SELECT cityHash64(stock_code) % 3 as shard_id, count(DISTINCT stock_code) 
        FROM tick_data_intraday 
        WHERE toDate(trade_date) = '{DATE}'
        GROUP BY shard_id
        ORDER BY shard_id
    """
    dist_res = client.execute(dist_query)
    for row in dist_res:
        print(f"Shard {row[0]}: {row[1]} stocks collected")
        
    print("\nExpected Distribution:")
    total_dist_query = f"""
        SELECT cityHash64(stock_code) % 3 as shard_id, count(DISTINCT stock_code) 
        FROM stock_adjust_factor
        GROUP BY shard_id
        ORDER BY shard_id
    """
    total_dist_res = client.execute(total_dist_query)
    for row in total_dist_res:
        print(f"Shard {row[0]}: {row[1]} stocks total")

except Exception as e:
    print(f"ERROR: {e}")

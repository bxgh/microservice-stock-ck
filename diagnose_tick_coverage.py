
import sys
from clickhouse_driver import Client
import pandas as pd

# Config
HOST = '192.168.151.111' # Use one of the healthy nodes
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

    # 2. Get total expected stocks (from a reference table, e.g., yesterday's data or stock_basic if exists)
    # Trying to find a reference. stock_adjust_factor or stock_kline_daily usually covers all active stocks.
    # Let's verify active stocks from basic info or recent kline.
    print("Querying reference stock list (from stock_adjust_factor as proxy)...")
    # Assuming stock_adjust_factor has all stocks. Or use stock_kline_daily for a recent date.
    ref_stocks = client.execute(f"""
        SELECT DISTINCT stock_code FROM stock_adjust_factor
    """)
    ref_set = set([s[0] for s in ref_stocks])
    ref_count = len(ref_set)
    print(f"Reference Stock Count (Total Market): {ref_count}")

    if ref_count == 0:
        print("Warning: Reference table empty. Trying stock_kline_daily...")
        ref_stocks = client.execute("""
            SELECT DISTINCT stock_code FROM stock_kline_daily 
            WHERE trade_date > '2026-01-01'
        """)
        ref_set = set([s[0] for s in ref_stocks])
        ref_count = len(ref_set)
        print(f"Reference Stock Count (Active in 2026): {ref_count}")

    # 3. Calculate Missing
    missing_set = ref_set - collected_set
    missing_count = len(missing_set)
    
    print(f"\nMissing Stocks: {missing_count}")
    if ref_count > 0:
        print(f"Missing Ratio: {missing_count / ref_count:.2%}")
        print(f"Collected Ratio: {collected_count / ref_count:.2%}")

    # 4. Analyze Missing Stocks Distribution (Modulo Analysis)
    # Check if missing stocks have a specific pattern relative to shard count (3)
    if missing_count > 0:
        print("\nAnalyzing modulo distribution of missing stocks (hash(code) % 3)...")
        from cityhash import CityHash64 # Assuming python cityhash might not be available, let's use SQL for this if possible
        
        # We can simulate sharding logic. Usually it's cityHash64(stock_code) % 3 or similar.
        # Let's do it in ClickHouse to be sure.
        
        missing_list_sample = list(missing_set)[:100] # Take a sample
        # We will query CH to get the shard_num for these missing stocks
        
        # Create a temporary table or just query with IN clause if list is not too huge
        # Actually, let's just count how many collected stocks fall into each shard bucket
        
        print("Checking shard distribution of COLLECTED stocks in ClickHouse...")
        # Assuming the sharding key is stock_code and using cityHash64 (standard for CH)
        # We check modulo 3
        dist_query = f"""
            SELECT cityHash64(stock_code) % 3 as shard_id, count(DISTINCT stock_code) 
            FROM tick_data_intraday 
            WHERE toDate(trade_date) = '{DATE}'
            GROUP BY shard_id
            ORDER BY shard_id
        """
        dist_res = client.execute(dist_query)
        print("Shard Distribution (0, 1, 2):")
        for row in dist_res:
            print(f"Shard {row[0]}: {row[1]} stocks")
            
        # Expected distribution?
        print("\nExpected Distribution (Total Market):")
        total_dist_query = f"""
            SELECT cityHash64(stock_code) % 3 as shard_id, count(DISTINCT stock_code) 
            FROM stock_adjust_factor
            GROUP BY shard_id
            ORDER BY shard_id
        """
        try:
            total_dist_res = client.execute(total_dist_query)
            for row in total_dist_res:
                print(f"Shard {row[0]}: {row[1]} stocks")
        except:
             print("Could not query expected distribution.")

except Exception as e:
    print(f"ERROR: {e}")

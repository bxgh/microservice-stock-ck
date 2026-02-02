
import sys
from clickhouse_driver import Client

HOST = '192.168.151.111'
PORT = 9000
USER = 'admin'
PASSWORD = 'admin123'
DATABASE = 'stock_data'
DATE = '2026-02-02'

def get_prefix(code):
    # Normalize first
    code = code.split('.')[0]
    if len(code) >= 2:
        return code[:2]
    return "other"

try:
    client = Client(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE)
    
    print(f"Fetching metrics for {DATE}...")
    
    # Collected
    rows = client.execute(f"SELECT DISTINCT stock_code FROM tick_data_intraday WHERE toDate(trade_date) = '{DATE}'")
    collected_codes = set([r[0] for r in rows])
    
    # Reference
    rows = client.execute(f"SELECT DISTINCT stock_code FROM stock_adjust_factor")
    ref_codes = set([r[0] for r in rows])
    
    missing_codes = ref_codes - collected_codes
    
    print(f"Collected: {len(collected_codes)}")
    print(f"Missing: {len(missing_codes)}")
    
    # Analyze Prefixes
    def analyze_prefixes(codes, label):
        stats = {}
        for c in codes:
            p = get_prefix(c)
            stats[p] = stats.get(p, 0) + 1
        
        print(f"\n{label} Prefix Distribution:")
        for p in sorted(stats.keys()):
            print(f"  {p}xxxx: {stats[p]}")

    analyze_prefixes(collected_codes, "COLLECTED")
    analyze_prefixes(missing_codes, "MISSING")

except Exception as e:
    print(f"ERROR: {e}")

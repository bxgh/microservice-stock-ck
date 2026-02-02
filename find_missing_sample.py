
import sys
from clickhouse_driver import Client

HOST = '192.168.151.111'
PORT = 9000
USER = 'admin'
PASSWORD = 'admin123'
DATABASE = 'stock_data'
DATE = '2026-02-02'

try:
    client = Client(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE)
    
    # 1. Collected
    rows = client.execute(f"SELECT DISTINCT stock_code FROM tick_data_intraday WHERE toDate(trade_date) = '{DATE}'")
    collected_codes = set([r[0] for r in rows])
    
    # 2. Reference (Adjust Factor)
    rows = client.execute(f"SELECT DISTINCT stock_code FROM stock_adjust_factor")
    ref_codes = set([r[0] for r in rows])
    
    # 3. Find Missing
    # Normalize ref codes just in case (e.g. 000001.SZ -> 000001)
    normalized_ref = set()
    for c in ref_codes:
        c = c.split('.')[0]
        if c.startswith('sh') or c.startswith('sz'): c = c[2:]
        normalized_ref.add(c)
        
    missing = normalized_ref - collected_codes
    
    print(f"Sample 10 Missing Codes: {list(missing)[:10]}")

except Exception as e:
    print(f"ERROR: {e}")

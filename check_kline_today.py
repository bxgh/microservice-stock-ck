
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
    
    print(f"Checking stock_kline_daily for {DATE}...")
    count = client.execute(f"SELECT count() FROM stock_kline_daily WHERE trade_date = '{DATE}'")[0][0]
    print(f"K-Line Rows for Today: {count}")
    
    if count > 0:
        print("Checking sample stocks in K-Line for today:")
        rows = client.execute(f"SELECT stock_code FROM stock_kline_daily WHERE trade_date = '{DATE}' LIMIT 10")
        print([r[0] for r in rows])
        
    # Check Tick Data count for comparison
    tick_count = client.execute(f"SELECT count(DISTINCT stock_code) FROM tick_data_intraday WHERE toDate(trade_date) = '{DATE}'")[0][0]
    print(f"Tick Data Distinct Stocks: {tick_count}")

except Exception as e:
    print(f"ERROR: {e}")

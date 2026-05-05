
import pymysql

try:
    conn = pymysql.connect( host="127.0.0.1", port=36301, user="root", password="alwaysup@888", database="alwaysup")
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT code, trade_date, created_at FROM stock_kline_daily WHERE trade_date = '20260318' LIMIT 1")
    row = cursor.fetchone()
    print(f"March 18 record metadata: {row}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")

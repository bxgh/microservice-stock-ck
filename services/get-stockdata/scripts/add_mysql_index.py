
import pymysql
import os
import time

def add_index():
    host = '127.0.0.1'
    port = 36301
    user = os.getenv('GSD_DB_USER', 'root')
    password = os.getenv('GSD_DB_PASSWORD', 'dev_password')
    db = os.getenv('GSD_DB_NAME', 'stock_data')
    
    print(f"Connecting to MySQL ({host}:{port})...")
    conn = pymysql.connect(host=host, port=port, user=user, password=password, db=db)
    
    try:
        with conn.cursor() as cursor:
            print("Checking if index exists...")
            cursor.execute("SHOW INDEX FROM stock_kline_daily WHERE Key_name = 'idx_created_at_code'")
            if cursor.fetchone():
                print("Index 'idx_created_at_code' already exists.")
                return

            print("Creating index 'idx_created_at_code' on stock_kline_daily(created_at, code)...")
            print("This may take a while for 17M records...")
            start = time.time()
            # mixing code in index helps the secondary sort
            cursor.execute("CREATE INDEX idx_created_at_code ON stock_kline_daily (created_at, code)")
            end = time.time()
            print(f"Index created successfully in {end - start:.2f} seconds.")
    except Exception as e:
        print(f"Error creating index: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_index()

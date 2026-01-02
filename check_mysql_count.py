
import os
import pymysql
import sys

def check_count():
    host = os.getenv("GSD_DB_HOST")
    user = os.getenv("GSD_DB_USER", "root")
    password = os.getenv("GSD_DB_PASS", "root")
    db = os.getenv("GSD_DB_NAME", "stock_data")
    
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db,
            port=3306
        )
        with conn.cursor() as cursor:
            sql = "SELECT count(*) FROM kline_daily WHERE trade_date = '2025-12-31'"
            cursor.execute(sql)
            count = cursor.fetchone()[0]
            print(f"MySQL count for 2025-12-31: {count}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_count()

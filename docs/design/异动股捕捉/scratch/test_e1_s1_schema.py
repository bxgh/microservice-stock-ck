import pymysql
from clickhouse_driver import Client
import os

# MySQL Config
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 36301
MYSQL_USER = "root"
MYSQL_PASSWORD = "alwaysup@888"
MYSQL_DB = "alwaysup"

# ClickHouse Config
CK_HOST = "127.0.0.1"
CK_PORT = 9000
CK_DB = "stock_data"

def test_mysql_schema():
    print("Testing MySQL Schema...")
    conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DB)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DESC ads_l8_unified_signal")
            fields = {row[0]: row for row in cursor.fetchall()}
            
            # Check new fields
            new_fields = ['source_version', 'anomaly_category', 'component_score', 'is_pushed']
            for field in new_fields:
                if field in fields:
                    print(f"  [PASS] Field '{field}' exists in MySQL.")
                else:
                    print(f"  [FAIL] Field '{field}' missing in MySQL.")
            
            # Check index
            cursor.execute("SHOW INDEX FROM ads_l8_unified_signal WHERE Key_name = 'idx_category_pushed'")
            if cursor.fetchone():
                print("  [PASS] Index 'idx_category_pushed' exists in MySQL.")
            else:
                print("  [FAIL] Index 'idx_category_pushed' missing in MySQL.")
    finally:
        conn.close()

def test_clickhouse_schema():
    print("\nTesting ClickHouse Schema...")
    client = Client(host=CK_HOST, port=CK_PORT)
    try:
        res = client.execute(f"DESCRIBE TABLE {CK_DB}.ads_l8_unified_signal_local")
        fields = {row[0]: row for row in res}
        
        new_fields = ['source_version', 'anomaly_category', 'component_score', 'is_pushed']
        for field in new_fields:
            if field in fields:
                print(f"  [PASS] Field '{field}' exists in ClickHouse.")
            else:
                print(f"  [FAIL] Field '{field}' missing in ClickHouse.")
    finally:
        client.disconnect()

if __name__ == "__main__":
    test_mysql_schema()
    test_clickhouse_schema()

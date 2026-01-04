import pymysql
try:
    conn = pymysql.connect(
        host='127.0.0.1', 
        user='root', 
        password='alwaysup@888', 
        database='alwaysup', 
        port=36301,
        connect_timeout=5
    )
    print("SUCCESS")
    conn.close()
except Exception as e:
    print(f"FAILED: {e}")

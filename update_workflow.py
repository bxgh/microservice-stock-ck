import pymysql
import os

host = "127.0.0.1"
port = 36301
user = "root"
password = "alwaysup@888" # Using the password from gsd-worker env
database = "alwaysup"

try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
    with conn.cursor() as cursor:
        sql = "UPDATE workflow_runs SET status = 'RUNNING' WHERE workflow_id = 'post_market_audit' AND status = 'PENDING'"
        affected = cursor.execute(sql)
        conn.commit()
        print(f"Updated {affected} workflow run(s) to RUNNING.")
        
        cursor.execute("SELECT run_id, workflow_id, status FROM workflow_runs WHERE status = 'RUNNING'")
        rows = cursor.fetchall()
        for row in rows:
            print(f"Active Run: {row}")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()

import pymysql
import json
from datetime import datetime

def check_tasks():
    conn = pymysql.connect(
        host='127.0.0.1',
        port=36301,
        user='root',
        password='alwaysup@888',
        database='alwaysup',
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cursor:
            # Check last 20 task executions
            cursor.execute("SELECT * FROM task_execution_logs ORDER BY start_time DESC LIMIT 20")
            rows = cursor.fetchall()
            for row in rows:
                # Convert datetime objects to string for JSON serialization
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
            print(json.dumps(rows, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    check_tasks()

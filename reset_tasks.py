import os
import pymysql

def reset_tasks():
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=36301,
            user='root',
            password='alwaysup@888',
            database='alwaysup'
        )
        with conn.cursor() as cursor:
            # 重置最近的 repair_tick 任务
            sql = "UPDATE task_commands SET status = 'PENDING' WHERE id IN (606, 607, 608)"
            cursor.execute(sql)
            conn.commit()
            print(f"✅ Reset {cursor.rowcount} tasks to PENDING")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_tasks()

import pymysql

try:
    conn = pymysql.connect(
        host="127.0.0.1",
        port=36301,
        user="root",
        password="alwaysup@888",
        database="alwaysup"
    )
    with conn.cursor() as cursor:
        sql = "UPDATE task_commands SET result = 'AI_DIAGNOSED: ALERT_ADMIN | Manual intervention to stop loop' WHERE id IN (21, 22)"
        affected = cursor.execute(sql)
        conn.commit()
        print(f"Manually diagnosed {affected} command(s).")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()

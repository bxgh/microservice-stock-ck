import pymysql
import json

try:
    conn = pymysql.connect(
        host="127.0.0.1",
        port=36301,
        user="root",
        password="alwaysup@888",
        database="alwaysup"
    )
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        rid = 'c512f3be-35c3-463e-9e3f-e56ce3acc70b'
        print(f"--- Workflow Run: {rid} ---")
        cursor.execute("SELECT * FROM workflow_runs WHERE run_id = %s", (rid,))
        run = cursor.fetchone()
        print(f"Status: {run['status']}")
        print(f"Context: {run['context']}")
        
        print("\n--- Commands ---")
        cursor.execute("SELECT id, step_id, task_id, status, result FROM task_commands WHERE run_id = %s", (rid,))
        commands = cursor.fetchall()
        for cmd in commands:
            print(cmd)
            
        print("\n--- Active Diagnosis (Other Runs) ---")
        cursor.execute("""
            SELECT c.id, c.task_id, c.status, c.result 
            FROM task_commands c 
            JOIN workflow_runs r ON c.run_id = r.run_id 
            WHERE c.status = 'FAILED' AND r.status = 'RUNNING' 
            AND c.result NOT LIKE 'AI_DIAGNOSED:%'
        """)
        failed = cursor.fetchall()
        for f in failed:
            print(f)
            
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()


import asyncio
import aiomysql
import json

mysql_config = {
    'host': '127.0.0.1', 
    'port': 36301, 
    'user': 'root', 
    'password': 'alwaysup@888', 
    'db': 'alwaysup', 
    'autocommit': True
}

async def check_workflow():
    try:
        conn = await aiomysql.connect(**mysql_config)
        async with conn.cursor() as cur:
            # 1. Check Workflow Run
            await cur.execute("SELECT run_id, workflow_id, status, start_time FROM workflow_runs WHERE workflow_id = 'noon_market_gate' ORDER BY start_time DESC LIMIT 1")
            row = await cur.fetchone()
            if row:
                run_id, wf_id, status, start = row
                print(f"--- Workflow Run: {wf_id} ---")
                print(f"Run ID: {run_id} | Status: {status} | Start: {start}")
                
                # 2. Check Tasks for this run
                await cur.execute("SELECT step_id, task_id, status, created_at, result FROM task_commands WHERE run_id = %s", (run_id,))
                tasks = await cur.fetchall()
                print("\n--- Steps ---")
                for t in tasks:
                    print(f"Step: {t[0]:<15} | Task: {t[1]:<25} | Status: {t[2]:<10} | Result: {t[4][:50] if t[4] else ''}")
            else:
                print("No workflow run found for noon_market_gate.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_workflow())

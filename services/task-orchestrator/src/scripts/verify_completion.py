import asyncio
import aiomysql
import sys
import json
import uuid
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings
from gsd_agent.core import SmartDecisionEngine
from core.flow_controller import FlowController

async def test_completion():
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        minsize=1,
        maxsize=5
    )

    # 1. Trigger Run
    run_id = str(uuid.uuid4())
    print(f"🚀 Triggering run {run_id}...")
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO alwaysup.workflow_runs (run_id, workflow_id, status, context) VALUES (%s, %s, %s, %s)",
                (run_id, "distributed_tick_sync_4.0", "RUNNING", json.dumps({"target_date": "20260125"}))
            )
            await conn.commit()

    # 2. Mock ALL steps as DONE
    steps = ["fetch_stock_list", "sync_shard_0", "sync_shard_1", "post_sync_audit"]
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for step_id in steps:
                await cursor.execute(
                    "INSERT INTO alwaysup.task_commands (run_id, step_id, task_id, status, result) VALUES (%s, %s, %s, %s, %s)",
                    (run_id, step_id, step_id, "DONE", "Success")
                )
            await conn.commit()

    # 3. Advance Run
    controller = FlowController(pool, None, None)
    print(">>> Advancing Run (Check for completion)...")
    await controller._process_active_runs()

    # 4. Verify status in DB
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT status, end_time FROM alwaysup.workflow_runs WHERE run_id = %s", (run_id,))
            run = await cursor.fetchone()
            print(f"\nFinal Run Status: {run['status']}")
            print(f"End Time: {run['end_time']}")
            
            if run['status'] == 'COMPLETED':
                print("\n✅ SUCCESS: Workflow run correctly transitioned to COMPLETED!")
            else:
                print("\n❌ FAILURE: Workflow run still in status:", run['status'])

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(test_completion())

import asyncio
import aiomysql
import sys
import uuid
import json
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

async def trigger_workflow(workflow_id: str, context: dict = None):
    """Trigger a new workflow run"""
    run_id = str(uuid.uuid4())
    
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        minsize=1,
        maxsize=5
    )

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO alwaysup.workflow_runs (run_id, workflow_id, status, context) VALUES (%s, %s, %s, %s)",
                (run_id, workflow_id, "RUNNING", json.dumps(context or {}))
            )
            await conn.commit()
    
    pool.close()
    await pool.wait_closed()
    print(f"🚀 Workflow Run '{run_id}' triggered successfully.")
    return run_id

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trigger_workflow.py <workflow_id> [context_json]")
        sys.exit(1)
    
    wf_id = sys.argv[1]
    ctx = {}
    if len(sys.argv) > 2:
        ctx = json.loads(sys.argv[2])
    
    asyncio.run(trigger_workflow(wf_id, ctx))

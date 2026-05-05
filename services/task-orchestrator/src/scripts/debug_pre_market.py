import asyncio
import aiomysql
import sys
import json
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings
from gsd_agent.core import SmartDecisionEngine
from core.flow_controller import FlowController

async def debug_pre_market():
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        minsize=1,
        maxsize=5
    )

    api_keys = {
        "deepseek": settings.DEEPSEEK_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "siliconflow": settings.SILICONFLOW_API_KEY
    }
    redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    agent = SmartDecisionEngine(api_keys=api_keys, redis_url=redis_url)
    controller = FlowController(pool, None, agent)

    print("\n" + "="*80)
    print("🔍 DEBUGGING PRE-MARKET WORKFLOW")
    print("="*80)

    # 1. Advance runs to emit Step 1
    print(">>> Advancing active runs...")
    await controller._process_active_runs()

    # 2. Mock Step 1 as DONE
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                UPDATE alwaysup.task_commands 
                SET status = 'DONE', result = 'Success' 
                WHERE step_id = 'fetch_stock_list' 
                AND run_id IN (SELECT run_id FROM alwaysup.workflow_runs WHERE workflow_id = 'pre_market_prep_4.0' AND status = 'RUNNING')
            """)
            await conn.commit()
            print(">>> Mocked Step 1 (fetch_stock_list) as DONE")

    # 3. Advance runs again to emit Step 2
    print(">>> Advancing runs for Step 2...")
    await controller._process_active_runs()

    # 4. Check for newly emitted commands
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("""
                SELECT id, step_id, task_id, status 
                FROM alwaysup.task_commands 
                WHERE run_id IN (SELECT run_id FROM alwaysup.workflow_runs WHERE workflow_id = 'pre_market_prep_4.0' AND status = 'RUNNING')
                ORDER BY id DESC LIMIT 5
            """)
            cmds = await cursor.fetchall()
            for c in cmds:
                print(f"Emitted: ID {c['id']} | Step: {c['step_id']} | Task: {c['task_id']} | Status: {c['status']}")

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(debug_pre_market())

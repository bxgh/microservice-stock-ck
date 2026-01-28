import asyncio
import aiomysql
import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings
from gsd_agent.core import SmartDecisionEngine
from core.flow_controller import FlowController

async def verify_loop():
    # 0. Mock API Keys (not needed for step transition, but needed for engine)
    agent = SmartDecisionEngine(api_keys={}, redis_url="redis://localhost:6379/1")
    
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        minsize=1,
        maxsize=5
    )

    controller = FlowController(pool, None, agent)
    
    print("\n>>> Advancing active runs...")
    await controller._process_active_runs()
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            print("\n>>> Task Commands Status:")
            await cursor.execute("SELECT id, step_id, task_id, status FROM alwaysup.task_commands ORDER BY id DESC LIMIT 5")
            cmds = await cursor.fetchall()
            for c in cmds:
                print(c)

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(verify_loop())

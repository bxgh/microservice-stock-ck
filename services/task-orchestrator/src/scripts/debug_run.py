import asyncio
import os
import aiomysql
from config.settings import settings

RUN_ID = "22a52dac-50fa-4dbc-800b-3eb7fdc585ac"

async def main():
    pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE
    )
    
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            print(f"--- Workflow Run: {RUN_ID} ---")
            await cursor.execute("SELECT * FROM alwaysup.workflow_runs WHERE run_id = %s", (RUN_ID,))
            run = await cursor.fetchone()
            print(f"Run Status: {run['status']}")
            print(f"Context: {run['context']}")
            
            print("\n--- Task Commands ---")
            await cursor.execute("SELECT * FROM alwaysup.task_commands WHERE run_id = %s ORDER BY id", (RUN_ID,))
            cmds = await cursor.fetchall()
            for cmd in cmds:
                print(f"ID: {cmd['id']}")
                print(f"Step: {cmd['step_id']}")
                print(f"Task: {cmd['task_id']}")
                print(f"Status: {cmd['status']}")
                print(f"Params: {cmd['params']}")
                print(f"Result: {cmd['result']}")
                print("-" * 30)

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())

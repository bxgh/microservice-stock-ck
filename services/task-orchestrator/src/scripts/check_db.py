import asyncio
import aiomysql
import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

async def check_db():
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
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            print("\n>>> Process List:")
            await cursor.execute("SHOW FULL PROCESSLIST")
            processes = await cursor.fetchall()
            for p in processes:
                if p['Command'] != 'Sleep':
                    print(f"ID: {p['Id']}, User: {p['User']}, Host: {p['Host']}, DB: {p['db']}, Command: {p['Command']}, Time: {p['Time']}, State: {p['State']}, Info: {p['Info']}")
            
            print("\n>>> Latest 10 Commands:")
            await cursor.execute("SELECT id, step_id, task_id, status, result, output_context FROM alwaysup.task_commands ORDER BY id DESC LIMIT 10")
            cmds = await cursor.fetchall()
            for c in cmds:
                print(c)
            
            print("\n>>> Migration History:")
            try:
                await cursor.execute("SELECT * FROM alwaysup.migrations_history")
                history = await cursor.fetchall()
                for h in history:
                    print(h)
            except Exception as e:
                print(f"Error reading history: {e}")

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(check_db())

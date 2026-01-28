import asyncio
import aiomysql
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import settings

async def kill_blocking_queries():
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
            await cursor.execute("SHOW FULL PROCESSLIST")
            processes = await cursor.fetchall()
            for p in processes:
                # Kill queries running for more than 60 seconds that are "Query"
                # But don't kill the ALTER TABLE itself (we want that one to finish!)
                if p['Time'] > 60 and p['Command'] == 'Query' and "ALTER TABLE" not in (p['Info'] or ""):
                    print(f"Killing process {p['Id']} (Time: {p['Time']}) - {p['Info'][:100]}")
                    try:
                        await cursor.execute(f"KILL {p['Id']}")
                    except Exception as e:
                        print(f"Failed to kill {p['Id']}: {e}")

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(kill_blocking_queries())

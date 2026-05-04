import asyncio
import aiomysql
import os

async def check_count():
    config = {
        "host": "127.0.0.1",
        "port": 36301,
        "user": "root",
        "password": "alwaysup@888",
        "db": "alwaysup"
    }
    try:
        conn = await aiomysql.connect(**config)
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM daily_basic")
            res = await cur.fetchone()
            print(f"MYSQL_COUNT:{res[0]}")
        conn.close()
    except Exception as e:
        print(f"ERROR:{e}")

if __name__ == "__main__":
    asyncio.run(check_count())

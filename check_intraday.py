
import asyncio
import aiomysql
from datetime import datetime

mysql_config = {
    'host': '127.0.0.1', 
    'port': 36301, 
    'user': 'root', 
    'password': 'alwaysup@888', 
    'db': 'alwaysup', 
    'autocommit': True
}

async def check():
    try:
        conn = await aiomysql.connect(**mysql_config)
        async with conn.cursor() as cur:
            await cur.execute("SELECT task_id, status, created_at FROM task_commands WHERE created_at >= CURDATE() AND task_id LIKE '%intraday%' ORDER BY created_at DESC")
            print("--- Intraday Commands (Today) ---")
            for r in await cur.fetchall():
                print(f"Task: {r[0]:<30} | Status: {r[1]:<10} | Created: {r[2]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())

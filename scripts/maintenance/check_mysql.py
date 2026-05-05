
import asyncio
import aiomysql
import os

async def check_count():
    try:
        pool = await aiomysql.create_pool(
            host='127.0.0.1', port=36301, user=os.getenv('GSD_DB_USER'), password=os.getenv('GSD_DB_PASSWORD'), db=os.getenv('GSD_DB_NAME'), charset='utf8mb4'
        )
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT count(*) FROM stock_kline_daily WHERE trade_date = '2025-12-25'")
                print(f"Count for 2025-12-25: {await cur.fetchone()}")
        pool.close()
        await pool.wait_closed()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_count())

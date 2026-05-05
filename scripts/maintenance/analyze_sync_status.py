
import asyncio
import aiomysql
import os
from datetime import datetime, timedelta

async def analyze_data():
    # 1. Check MySQL created_at distribution
    print("--- MySQL Analysis ---")
    try:
        pool = await aiomysql.create_pool(
            host='127.0.0.1', port=36301, user=os.getenv('GSD_DB_USER'), password=os.getenv('GSD_DB_PASSWORD'), db=os.getenv('GSD_DB_NAME'), charset='utf8mb4'
        )
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Check min/max created_at
                await cur.execute("SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM stock_kline_daily")
                min_created, max_created, total = await cur.fetchone()
                print(f"Total Records: {total}")
                print(f"Min created_at: {min_created}")
                print(f"Max created_at: {max_created}")
                
                # Check count in last 48 hours
                start_time = datetime.now() - timedelta(hours=48)
                await cur.execute("SELECT COUNT(*) FROM stock_kline_daily WHERE created_at >= %s", (start_time,))
                recent_count = await cur.fetchone()
                print(f"Records created in last 48h: {recent_count[0]}")
                
        pool.close()
        await pool.wait_closed()
    except Exception as e:
        print(f"MySQL Error: {e}")

    # 2. Check ClickHouse Status (via HTTP or assuming verify script)
    # Since we can't easily run CH query from here without asynch setup, 
    # we will rely on previous knowledge that CH has data, but let's try if library available.
    print("\n--- ClickHouse Analysis ---")
    try:
        import asynch
        ch_pool = await asynch.create_pool(
            host='127.0.0.1', port=9000, user='admin', password='admin123', database='stock_data'
        )
        async with ch_pool.acquire() as ch_conn:
            async with ch_conn.cursor() as cursor:
                await cursor.execute("SELECT count(*) FROM stock_kline_daily")
                ch_total = (await cursor.fetchone())[0]
                print(f"ClickHouse Total Records: {ch_total}")
                
                await cursor.execute("SELECT min(trade_date), max(trade_date) FROM stock_kline_daily")
                ch_range = await cursor.fetchone()
                print(f"ClickHouse Date Range: {ch_range[0]} to {ch_range[1]}")

        ch_pool.close()
        await ch_pool.wait_closed()
    except Exception as e:
        print(f"ClickHouse Error: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_data())

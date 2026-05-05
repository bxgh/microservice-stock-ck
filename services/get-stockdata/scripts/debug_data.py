
import asyncio
import pandas as pd
import sys
import os

# Add src to sys.path
sys.path.append('/app/src')

from data_access import ClickHousePoolManager, ClickHouseKLineDAO, MySQLPoolManager, KLineDAO

async def check():
    print("--- Checking ClickHouse ---")
    try:
        pool = await ClickHousePoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT count() FROM stock_kline_daily")
                row = await cursor.fetchone()
                print(f"Total records in ClickHouse: {row[0]}")
                
                await cursor.execute("SELECT stock_code, max(trade_date) FROM stock_kline_daily GROUP BY stock_code LIMIT 5")
                rows = await cursor.fetchall()
                print("Latest dates in ClickHouse:")
                for r in rows:
                    print(f"  {r[0]}: {r[1]}")
    except Exception as e:
        print(f"ClickHouse Check Failed: {e}")

    print("\n--- Checking MySQL ---")
    try:
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT count(*) FROM stock_kline_daily")
                row = await cursor.fetchone()
                print(f"Total records in MySQL: {row[0]}")
                
                await cursor.execute("SELECT code, max(trade_date) FROM stock_kline_daily GROUP BY code LIMIT 5")
                rows = await cursor.fetchall()
                print("Latest dates in MySQL:")
                for r in rows:
                    print(f"  {r[0]}: {r[1]}")
    except Exception as e:
        print(f"MySQL Check Failed: {e}")

if __name__ == "__main__":
    asyncio.run(check())

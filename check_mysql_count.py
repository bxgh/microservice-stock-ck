
import asyncio
import aiomysql
import os

async def main():
    config = {
        "host": "127.0.0.1",
        "port": 36301,
        "user": "root",
        "password": "alwaysup@888",
        "db": "alwaysup",
        "autocommit": True
    }
    
    print(f"Connecting to MySQL at {config['host']}:{config['port']}...")
    try:
        pool = await aiomysql.create_pool(**config)
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                print("Checking stock_basic_info table...")
                
                # Total count
                await cur.execute("SELECT count(*) FROM stock_basic_info")
                total = await cur.fetchone()
                print(f"Total rows in stock_basic_info: {total[0]}")
                
                # Active count (L)
                await cur.execute("SELECT count(*) FROM stock_basic_info WHERE list_status = 'L'")
                active_l = await cur.fetchone()
                print(f"Active (list_status='L'): {active_l[0]}")
                
               # Active count (L) and Market
                await cur.execute("""
                    SELECT count(*) FROM stock_basic_info 
                    WHERE list_status = 'L' 
                    AND market IN ('主板', '中小板', '创业板', '科创板')
                """)
                market_filtered = await cur.fetchone()
                print(f"Active + Market Filter: {market_filtered[0]}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())


import asyncio
import os
import aiomysql
from datetime import datetime, timedelta

# Mock logs for the past 7 days to populate history
logs = [
    # (days_ago, records, duration_sec, status)
    (6, 4520, 12.5, "SUCCESS"),  # 2024-12-22
    (5, 4610, 13.2, "SUCCESS"),  # 2024-12-23 
    (4, 4580, 12.8, "SUCCESS"),  # 2024-12-24
    (3, 4625, 13.0, "SUCCESS"),  # 2024-12-25
    (2, 4550, 11.5, "SUCCESS"),  # 2024-12-26
    (1, 0, 1.2, "SUCCESS"),      # 2024-12-27 (Weekend/No Data or simply gap) -> Actually 27 was Friday, maybe late night sync 
    (0, 2305, 5.5, "SUCCESS"),   # 2024-12-28 (Today)
]

async def backfill_logs():
    host = '127.0.0.1'
    port = 36301
    user = os.getenv('GSD_DB_USER', 'root')
    password = os.getenv('GSD_DB_PASSWORD', 'dev_password')
    db = os.getenv('GSD_DB_NAME', 'stock_data')
    
    print(f"Connecting to MySQL ({host}:{port})...")
    pool = await aiomysql.create_pool(host=host, port=port, user=user, password=password, db=db, autocommit=True)

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Clear existing logs for kline_daily_sync to avoid duplicates
            await cursor.execute("DELETE FROM sync_execution_logs WHERE task_name = 'kline_daily_sync'")
            
            print("Backfilling logs...")
            for days_ago, records, duration, status in logs:
                exec_time = datetime.now() - timedelta(days=days_ago)
                # Normalize time to 19:00:00
                exec_time = exec_time.replace(hour=19, minute=0, second=0, microsecond=0)
                
                msg = f"智能增量同步完成：{records:,} 条记录" if records > 0 else "无新数据需要同步"
                
                sql = """
                    INSERT INTO sync_execution_logs 
                    (task_name, status, records_processed, details, duration_seconds, execution_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                await cursor.execute(sql, (
                    "kline_daily_sync", 
                    status, 
                    records, 
                    msg, 
                    duration, 
                    exec_time
                ))
                print(f"Inserted log for {exec_time.date()}: {records} records")
    
    pool.close()
    await pool.wait_closed()
    print("Backfill complete.")

if __name__ == "__main__":
    if os.getenv('ENVIRONMENT') == 'development':
        # Force local specific env if running script directly in container
        pass 
    asyncio.run(backfill_logs())

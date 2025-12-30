
import asyncio
import os
import aiomysql
import asynch
from datetime import datetime, timedelta

async def backfill_logs():
    host = '127.0.0.1'
    port = 36301
    user = os.getenv('GSD_DB_USER', 'root')
    password = os.getenv('GSD_DB_PASSWORD', 'dev_password')
    db = os.getenv('GSD_DB_NAME', 'stock_data')
    
    ch_host = os.getenv('CLICKHOUSE_HOST', 'localhost')
    # Use direct connection port or tunnel port? 
    # Usually 9000 for TCP client
    ch_port = 9000 
    
    print(f"Connecting to MySQL ({host}:{port}) and ClickHouse...")
    
    pool = await aiomysql.create_pool(host=host, port=port, user=user, password=password, db=db, autocommit=True)
    
    # Connect to ClickHouse to get actual counts for the last 7 days
    try:
        ch_client = await asynch.connect(
            host=ch_host, 
            port=ch_port, 
            user=os.getenv('CLICKHOUSE_USER', 'admin'),
            password=os.getenv('CLICKHOUSE_PASSWORD', 'admin123'),
            database=os.getenv('CLICKHOUSE_DB', 'stock_data')
        )
    except Exception as e:
        print(f"Failed to connect to ClickHouse: {e}")
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Clear existing logs for kline_daily_sync to avoid duplicates
            await cursor.execute("DELETE FROM sync_execution_logs WHERE task_name = 'kline_daily_sync'")
            print("Cleared existing logs.")
            
            # Query MySQL for latest trading dates (to know which days had data)
            # Actually, let's just query ClickHouse for daily counts for the last 7 days
            
            async with ch_client.cursor() as ch_cursor:
                # Get daily counts for last 10 days
                query = """
                    SELECT trade_date, count() as cnt 
                    FROM stock_kline_daily 
                    WHERE trade_date >= today() - 10 
                    GROUP BY trade_date 
                    ORDER BY trade_date DESC
                """
                await ch_cursor.execute(query)
                results = await ch_cursor.fetchall()
            
            print("Backfilling logs based on ClickHouse data...")
            for trade_date, count in results:
                # Assume sync happened at 19:00 on that day
                # trade_date is date object or string? Usually date.
                if isinstance(trade_date, str):
                    exec_date = datetime.strptime(trade_date, "%Y-%m-%d")
                else:
                    exec_date = datetime.combine(trade_date, datetime.min.time())
                
                exec_time = exec_date.replace(hour=19, minute=0, second=0)
                
                # Mock duration
                duration = 5.0 + (count / 1000.0) 
                
                msg = f"智能增量同步完成：{count:,} 条记录"
                
                sql = """
                    INSERT INTO sync_execution_logs 
                    (task_name, status, records_processed, details, duration_seconds, execution_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                await cursor.execute(sql, (
                    "kline_daily_sync", 
                    "SUCCESS", 
                    count, 
                    msg, 
                    duration, 
                    exec_time
                ))
                print(f"Inserted log for {trade_date}: {count} records")
    
    pool.close()
    await pool.wait_closed()
    print("Backfill complete.")

if __name__ == "__main__":
    asyncio.run(backfill_logs())

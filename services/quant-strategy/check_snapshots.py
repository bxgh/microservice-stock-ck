
import asyncio
from adapters.clickhouse_loader import ClickHouseLoader

async def check_snapshots():
    loader = ClickHouseLoader()
    await loader.initialize()
    try:
        # 1. 检查 snapshot_data_local
        print("--- snapshot_data_local Statistics ---")
        query = """
        SELECT toDate(snapshot_time) as d, COUNT(*) 
        FROM stock_data.snapshot_data_local 
        GROUP BY d 
        ORDER BY d DESC 
        LIMIT 5
        """
        result = loader.client.execute(query)
        for row in result:
            print(row)
            
        # 2. 检查最近一天的股票数
        if result:
            latest_date = result[0][0]
            query_stocks = f"SELECT COUNT(DISTINCT stock_code) FROM stock_data.snapshot_data_local WHERE toDate(snapshot_time)='{latest_date}'"
            count = loader.client.execute(query_stocks)[0][0]
            print(f"\nStocks covered on {latest_date}: {count}")
            
    finally:
        await loader.close()

if __name__ == "__main__":
    asyncio.run(check_snapshots())

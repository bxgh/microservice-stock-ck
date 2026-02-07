
import asyncio
from adapters.clickhouse_loader import ClickHouseLoader
from config.settings import settings

async def check_data():
    loader = ClickHouseLoader()
    await loader.initialize()
    try:
        # 查询最近 5 天的数据量
        query = "SELECT snapshot_date, COUNT(*) FROM intraday_local GROUP BY snapshot_date ORDER BY snapshot_date DESC LIMIT 5"
        result = loader.client.execute(query)
        print("Data availability (snapshot_date, count):")
        for row in result:
            print(row)
            
        # 查询股票池覆盖度
        query_coverage = "SELECT COUNT(DISTINCT stock_code) FROM intraday_local WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM intraday_local)"
        coverage = loader.client.execute(query_coverage)
        print(f"\nLast date stock coverage: {coverage[0][0]}")
        
    finally:
        await loader.close()

if __name__ == "__main__":
    asyncio.run(check_data())

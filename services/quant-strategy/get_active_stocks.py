
import asyncio
from adapters.clickhouse_loader import ClickHouseLoader

async def get_active_stocks():
    loader = ClickHouseLoader()
    await loader.initialize()
    target_date = "2026-02-05"
    try:
        # 选取成交额前 500 的股票
        query = f"""
        SELECT stock_code, MAX(total_amount) as amnt
        FROM stock_data.snapshot_data_distributed
        WHERE toDate(trade_date) = '{target_date}'
        GROUP BY stock_code
        ORDER BY amnt DESC
        LIMIT 500
        """
        result = loader.client.execute(query)
        codes = [row[0] for row in result]
        print(f"Top 500 stocks on {target_date}:")
        print(codes[:10], "... total", len(codes))
        
        with open("active_stocks_0205.txt", "w") as f:
            for code in codes:
                f.write(f"{code}\n")
                
    finally:
        await loader.close()

if __name__ == "__main__":
    asyncio.run(get_active_stocks())

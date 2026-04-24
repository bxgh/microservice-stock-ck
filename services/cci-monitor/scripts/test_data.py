import asyncio
import pandas as pd
from src.data.api_client import MySQLDataClient
from src.data.cache import ParquetCache, CachedDataSource
from src.utils.dates import trading_calendar
from src.core.logger import setup_logger

async def test_data_layer():
    setup_logger()
    print("🚀 Starting Data Layer test...")
    
    # 1. 初始化客户端
    client = MySQLDataClient(base_url="http://127.0.0.1:8085") # 测试内部回环
    # 注意：实际上 8085 是 cci-monitor 自己的端口，get-stockdata 应该在别的端口。
    # 根据 41 服务器习惯，get-stockdata 应该在 8000 左右，或者通过 nacos 发现。
    # 这里我们使用 settings 中定义的 GSD_API_URL。
    
    from src.config.settings import settings
    print(f"📡 Using GSD_API_URL: {settings.GSD_API_URL}")
    
    base_client = MySQLDataClient(base_url=settings.GSD_API_URL)
    cache = ParquetCache()
    data_source = CachedDataSource(base_client, cache)
    
    # 2. 测试获取 K 线
    try:
        print("📥 Fetching 000300.SH klines...")
        df = await data_source.fetch_kline("sh000300", start_date="2024-01-01", end_date="2024-01-10")
        if not df.empty:
            print(f"✅ Success! Got {len(df)} rows.")
            print(df.head())
        else:
            print("⚠️ Warning: Data is empty.")
    except Exception as e:
        print(f"❌ Error fetching kline: {e}")

    # 3. 测试交易日历
    print("📅 Testing trading calendar...")
    trading_calendar.data_client = data_source
    last_day = await trading_calendar.get_last_trading_day()
    print(f"✅ Last trading day: {last_day}")

if __name__ == "__main__":
    asyncio.run(test_data_layer())

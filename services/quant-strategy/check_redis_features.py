
import asyncio
from cache.feature_store import FeatureStore

async def check_redis_features():
    store = FeatureStore()
    trade_date = "2026-02-06"
    test_stocks = ["600519", "000001", "300750"]
    
    print(f"Checking features in Redis for {trade_date}...")
    features = await store.batch_get(test_stocks, trade_date)
    
    for code in test_stocks:
        if code in features:
            print(f"✅ {code}: Found features, shape {features[code].shape}")
        else:
            print(f"❌ {code}: No features found")

if __name__ == "__main__":
    asyncio.run(check_redis_features())

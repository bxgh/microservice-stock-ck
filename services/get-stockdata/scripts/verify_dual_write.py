import asyncio
import os
import sys
sys.path.append('/app')
import pandas as pd
from datetime import datetime
from src.core.storage.parquet_writer import ParquetWriter
from src.storage.clickhouse_writer import ClickHouseWriter
from src.core.storage.dual_writer import DualWriter

async def verify():
    print("🚀 Starting Dual Write Verification...")
    
    # 1. Initialize Writers
    parquet_path = "/app/data/snapshots_test"
    parquet_writer = ParquetWriter(parquet_path)
    
    clickhouse_host = os.getenv('CLICKHOUSE_HOST', 'microservice-stock-clickhouse')
    clickhouse_writer = ClickHouseWriter(
        host=clickhouse_host,
        port=int(os.getenv('CLICKHOUSE_PORT', 9000)),
        database=os.getenv('CLICKHOUSE_DB', 'stock_data')
    )
    
    dual_writer = DualWriter(parquet_writer, clickhouse_writer)
    
    # 2. Create Dummy Data
    timestamp = datetime.now()
    df = pd.DataFrame({
        'code': ['TEST001', 'TEST002'],
        'name': ['Test Stock 1', 'Test Stock 2'],
        'market': ['SZ', 'SH'],
        'price': [10.5, 20.0],
        'open': [10.0, 19.5],
        'high': [11.0, 20.5],
        'low': [9.5, 19.0],
        'last_close': [10.0, 19.0],
        'volume': [1000, 2000],
        'amount': [10500.0, 40000.0],
        # Bids
        'bid1': [10.4, 19.9], 'bid_vol1': [100, 200],
        'bid2': [10.3, 19.8], 'bid_vol2': [100, 200],
        'bid3': [10.2, 19.7], 'bid_vol3': [100, 200],
        'bid4': [10.1, 19.6], 'bid_vol4': [100, 200],
        'bid5': [10.0, 19.5], 'bid_vol5': [100, 200],
        # Asks
        'ask1': [10.6, 20.1], 'ask_vol1': [100, 200],
        'ask2': [10.7, 20.2], 'ask_vol2': [100, 200],
        'ask3': [10.8, 20.3], 'ask_vol3': [100, 200],
        'ask4': [10.9, 20.4], 'ask_vol4': [100, 200],
        'ask5': [11.0, 20.5], 'ask_vol5': [100, 200],
    })
    
    print(f"📝 Writing {len(df)} rows...")
    
    # 3. Write Data
    p_success, c_success = await dual_writer.write(df, timestamp)
    
    print(f"✅ Write Result: Parquet={p_success}, ClickHouse={c_success}")
    
    if not (p_success and c_success):
        print("❌ Write failed!")
        return

    # 4. Verify Parquet
    # Reconstruct path logic to find file
    date_str = timestamp.strftime('%Y-%m-%d')
    hour_str = timestamp.strftime('%H')
    time_str = timestamp.strftime('%Y%m%d_%H%M%S')
    expected_path = f"{parquet_path}/{date_str}/{hour_str}/snapshot_{time_str}.parquet"
    
    if os.path.exists(expected_path):
        print(f"✅ Parquet file exists: {expected_path}")
    else:
        print(f"❌ Parquet file missing: {expected_path}")
        
    # 5. Verify ClickHouse
    print("🔍 Querying ClickHouse...")
    # Give it a moment to flush if async (though we called flush in writer)
    await asyncio.sleep(1)
    
    try:
        result = clickhouse_writer.query(f"SELECT count() FROM snapshot_data WHERE stock_code IN ('TEST001', 'TEST002') AND toDate(snapshot_time) = today()")
        count = result[0][0]
        print(f"📊 ClickHouse count: {count}")
        if count >= 2:
            print("✅ ClickHouse verification successful")
        else:
            print("❌ ClickHouse verification failed (count mismatch)")
    except Exception as e:
        print(f"❌ ClickHouse query failed: {e}")

    dual_writer.close()

if __name__ == "__main__":
    asyncio.run(verify())

import asyncio
import grpc
import sys
import os
import json
import pandas as pd

# Add paths for proto and service
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(base_dir, "../../libs/common"))

from datasource.v1 import data_source_pb2
from datasource.v1 import data_source_pb2_grpc

async def test_fetch(stub, data_type, codes, params=None, label=""):
    print(f"\n>>> TESTING: {label} ({data_type})")
    request = data_source_pb2.DataRequest(
        type=data_type,
        codes=codes,
        params=params or {}
    )
    
    try:
        response = await stub.FetchData(request)
        if response.success:
            data = json.loads(response.json_data)
            print(f"✅ SUCCESS: {response.source_name} returned {len(data)} records")
            print(f"   Latency: {response.latency_ms}ms")
            if data:
                df = pd.DataFrame(data)
                print(f"   Sample data (first row):")
                print(df.iloc[0].to_dict())
        else:
            print(f"❌ FAILED: {response.error_message}")
            print(f"   Source: {response.source_name}")
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")

async def main():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = data_source_pb2_grpc.DataSourceServiceStub(channel)
        
        print("Starting mootdx-source gRPC Interface Deep Dive...")
        
        # 1. QUOTES
        await test_fetch(stub, data_source_pb2.DATA_TYPE_QUOTES, ["600519", "000001"], label="Realtime Quotes")
        
        # 2. TICK
        await test_fetch(stub, data_source_pb2.DATA_TYPE_TICK, ["600519"], label="Tick Data")
        
        # 3. HISTORY (Baostock -> Mootdx)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_HISTORY, ["600519"], 
                         params={"start_date": "2023-01-01", "end_date": "2023-01-10"}, 
                         label="History K-Line")
        
        # 4. FINANCE (Akshare -> Baostock)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_FINANCE, ["600519"], label="Financial Data")
        
        # 5. VALUATION (Akshare)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_VALUATION, ["600519"], label="Valuation Data")
        
        # 6. INDUSTRY (Baostock -> Akshare)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_INDUSTRY, ["600519"], label="Industry Info")
        
        # 7. RANKING (Akshare)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_RANKING, [], 
                         params={"ranking_type": "hot"}, label="Hot Ranking")

if __name__ == "__main__":
    asyncio.run(main())

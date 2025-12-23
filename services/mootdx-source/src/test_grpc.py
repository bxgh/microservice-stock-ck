import asyncio
import grpc
import sys
import os
import json
import pandas as pd

# In container, libs/common is already in PYTHONPATH
# But we need to make sure we can find datasource.v1
try:
    from datasource.v1 import data_source_pb2
    from datasource.v1 import data_source_pb2_grpc
except ImportError:
    # Fallback for manual pathing
    sys.path.append("/app/libs/common")
    from datasource.v1 import data_source_pb2
    from datasource.v1 import data_source_pb2_grpc

async def test_fetch(stub, data_type, codes, params=None, label=""):
    print(f"\n" + "="*60)
    print(f">>> TESTING: {label} ({data_source_pb2.DataType.Name(data_type)})")
    print(f"    Codes: {codes}, Params: {params}")
    print("="*60)
    
    request = data_source_pb2.DataRequest(
        type=data_type,
        codes=codes,
        params=params or {}
    )
    
    try:
        start_time = asyncio.get_event_loop().time()
        response = await stub.FetchData(request)
        end_time = asyncio.get_event_loop().time()
        
        if response.success:
            data = json.loads(response.json_data)
            print(f"✅ SUCCESS: {response.source_name} returned {len(data)} records")
            print(f"   gRPC Latency (server): {response.latency_ms}ms")
            print(f"   Total Round-trip: {int((end_time - start_time) * 1000)}ms")
            if data:
                df = pd.DataFrame(data)
                print(f"   Sample data (first row):")
                print(df.iloc[0].to_dict())
                if 'code' in df.columns:
                    print(f"   Unique codes: {df['code'].unique().tolist()}")
        else:
            print(f"❌ FAILED: {response.error_message}")
            print(f"   Source: {response.source_name}")
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")

async def main():
    # Use 127.0.0.1 since we are in host mode OR the container itself
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = data_source_pb2_grpc.DataSourceServiceStub(channel)
        
        print("\n" + "#"*60)
        print("MOOTDX-SOURCE GRPC INTERFACE DEEP DIVE")
        print("#"*60)
        
        # 1. QUOTES (Mootdx)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_QUOTES, ["600519", "000001"], label="Realtime Quotes")
        
        # 2. TICK (Mootdx)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_TICK, ["600519"], label="Tick Data")
        
        # 3. HISTORY (Baostock -> Mootdx fallback)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_HISTORY, ["600519"], 
                         params={"start_date": "2025-12-01", "end_date": "2025-12-10"}, 
                         label="History K-Line (Expect Baostock)")
        
        # 4. FINANCE (Akshare -> Baostock fallback)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_FINANCE, ["600519"], label="Financial Data (Expect Akshare)")
        
        # 5. VALUATION (Akshare)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_VALUATION, ["600519"], label="Valuation Data")
        
        # 6. INDUSTRY (Baostock -> Akshare fallback)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_INDUSTRY, ["601318"], label="Industry Info")
        
        # 7. RANKING (Akshare)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_RANKING, [], 
                         params={"ranking_type": "hot"}, label="Hot Ranking")
        
        # 8. META (Mootdx)
        await test_fetch(stub, data_source_pb2.DATA_TYPE_META, ["600519"], label="Stock Meta/Info")

if __name__ == "__main__":
    asyncio.run(main())

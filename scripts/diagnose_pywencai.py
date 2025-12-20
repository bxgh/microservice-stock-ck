import grpc
import sys
import os
import asyncio
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../libs/common")))

from datasource.v1 import data_source_pb2
from datasource.v1 import data_source_pb2_grpc

async def test_pywencai():
    # Get target from args or default
    target = sys.argv[1] if len(sys.argv) > 1 else 'localhost:50053'
    
    print(f"Connecting to {target}...")
    async with grpc.aio.insecure_channel(target) as channel:
        stub = data_source_pb2_grpc.DataSourceServiceStub(channel)
        
        # 1. Health Check
        print("\n--- Testing Health Check ---")
        try:
            health = await stub.HealthCheck(data_source_pb2.Empty())
            print(f"Health Status: {health.healthy}")
            print(f"Message: {health.message}")
        except Exception as e:
            print(f"Health Check Failed: {e}")
            return

        # 2. Test Sector Data (This uses pywencai.get)
        print("\n--- Testing Sector Data (pywencai.get) ---")
        try:
            request = data_source_pb2.DataRequest(
                type=data_source_pb2.DATA_TYPE_SECTOR,
                params={"u_code": "000001"} # Dummy param
            )
            response = await stub.FetchData(request)
            if response.success:
                print("Fetch Success!")
                data = json.loads(response.json_data)
                print(f"Got {len(data)} items")
                if len(data) > 0:
                    print(f"Sample: {data[0]}")
            else:
                print(f"Fetch Failed: {response.error_message}")
        except Exception as e:
            print(f"RPC Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pywencai())

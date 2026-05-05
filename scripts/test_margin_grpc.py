import grpc
import sys
import os
import pandas as pd
import asyncio

# 添加 mootdx-source 源码路径到 sys.path 以便导入 generated protos
sys.path.append(os.path.abspath("services/mootdx-source/src"))

from datasource.v1 import data_source_pb2, data_source_pb2_grpc

async def test_margin_grpc():
    print("Testing gRPC MARGIN entry point...")
    
    # 建立异步连接
    channel = grpc.aio.insecure_channel("localhost:50051")
    stub = data_source_pb2_grpc.DataSourceServiceStub(channel)
    
    # 构造请求 (融资数据通常是全市场的汇总，codes 可以为空或 ["all"])
    request = data_source_pb2.DataRequest(
        type=data_source_pb2.DATA_TYPE_MARGIN,
        codes=["all"],
        params={"start_date": "2024-01-01"}
    )
    
    try:
        print("Sending request to mootdx-source...")
        response = await stub.FetchData(request)
        
        if not response.success:
            print(f"FAILED: {response.error_message}")
            return
            
        print(f"SUCCESS! Source: {response.source_name}, Latency: {response.latency_ms}ms")
        
        if not response.json_data or response.json_data == "[]":
            print("Response JSON is empty. Ensure market_margin_summary table is populated.")
            return

        # 解析数据
        df = pd.read_json(response.json_data)
        print("\nFetched Data (Head):")
        print(df.head())
        
        # 校验字段
        required = ["trade_date", "margin_buy", "margin_balance"]
        for col in required:
            if col not in df.columns:
                print(f"MISSING COLUMN: {col}")
            else:
                print(f"Found column: {col}")
                
    except Exception as e:
        print(f"Error during gRPC call: {e}")
    finally:
        await channel.close()

if __name__ == "__main__":
    asyncio.run(test_margin_grpc())

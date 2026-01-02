
import asyncio
import os
import sys
import pandas as pd

# Add the source directory to sys.path to import internal modules
sys.path.append("/home/bxgh/microservice-stock/services/data-collector/src")

from grpc_client.client import DataSourceClient

async def test():
    # Use localhost:50051 since mootdx-source is on host network
    client = DataSourceClient(server_url="localhost:50051")
    try:
        await client.initialize()
        print("Connected to mootdx-source")
        
        # Test fetching stock list metadata
        print("Fetching stock list...")
        df = await client.fetch_meta("all")
        if df.empty:
            print("Stock list is empty")
        else:
            print(f"Successfully fetched {len(df)} stocks")
            print(df.head())
        
        # Test fetching kline for one stock for 2025-12-31
        print("Fetching K-line for sh.600000 on 2025-12-31...")
        df_kline = await client.fetch_history(
            code="sh.600000",
            start_date="2025-12-31",
            end_date="2025-12-31",
            frequency="d",
            adjust="3"
        )
        if df_kline.empty:
            print("K-line is empty")
        else:
            print(f"Successfully fetched K-line")
            print(df_kline)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test())

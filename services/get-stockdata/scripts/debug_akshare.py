import asyncio
import logging
import sys
import os

logging.basicConfig(level=logging.DEBUG)
sys.path.insert(0, "/app/src")

from data_sources.providers.akshare_provider import AkshareProvider
from data_sources.providers.base import DataType

async def main():
    print("Initializing...")
    p = AkshareProvider()
    await p.initialize()
    print("Fetching Ranking (Hot)...")
    try:
        res = await p.fetch(DataType.RANKING, ranking_type="hot")
        print(f"Ranking Result: {res}")
        if res.error:
            print(f"RANKING ERROR: {res.error}")
    except Exception as e:
        print(f"RANKING EXCEPTION: {e}")

    print("-" * 20) 

    print("Fetching Index (HS300)...")
    try:
        res = await p.fetch(DataType.INDEX, index_code="000300")
        print(f"Index Result: {res}")
        if res.error:
            print(f"INDEX ERROR: {res.error}")
    except Exception as e:
        print(f"INDEX EXCEPTION: {e}")
    await p.close()

if __name__ == "__main__":
    asyncio.run(main())

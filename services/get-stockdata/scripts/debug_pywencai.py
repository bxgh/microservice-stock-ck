import asyncio
import logging
import sys
import os

logging.basicConfig(level=logging.DEBUG)
sys.path.insert(0, "/app/src")

from data_sources.providers.pywencai_provider import PywencaiProvider
from data_sources.providers.base import DataType

async def main():
    print("Initializing...")
    p = PywencaiProvider()
    await p.initialize()
    print("Querying 600519...")
    try:
        res = await p.fetch(DataType.SCREENING, query="600519")
        print(f"Result: {res}")
        if res.error:
            print(f"ERROR: {res.error}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
    await p.close()

if __name__ == "__main__":
    asyncio.run(main())

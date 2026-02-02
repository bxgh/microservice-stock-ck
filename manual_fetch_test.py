
import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL_BASE = "http://127.0.0.1:8003/api/v1/tick/"

async def fetch(code):
    url = f"{URL_BASE}{code}"
    print(f"Fetching {url}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"start": 0}) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Data Length: {len(data)}")
                    if len(data) > 0:
                        print(f"Sample: {data[0]}")
                else:
                    print(f"Error Body: {await resp.text()}")
    except Exception as e:
        print(f"Exception: {e}")

async def main():
    print("--- Testing Missing Stock 000913 ---")
    await fetch("000913")
    
    print("\n--- Testing Collected Stock 000001 ---")
    await fetch("000001")

if __name__ == "__main__":
    asyncio.run(main())

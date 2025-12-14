
import asyncio
import aiohttp
import sys
import os
import json

# Configuration
BASE_URL = "http://127.0.0.1:8083/api/v1"
TEST_STOCK = "600519"
TEST_BATCH_STOCKS = "600519,000001"

async def test_endpoint(session, name, url):
    print(f"\n[Test] {name}")
    print(f"URL: {url}")
    try:
        async with session.get(url) as response:
            status = response.status
            print(f"Status: {status}")
            
            if status == 200:
                try:
                    data = await response.json()
                    print(f"Response: Success")
                    # Preview data safely
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        print(f"Keys: {keys}")
                        if 'data' in data:
                            print(f"Data Preview: {str(data['data'])[:200]}...")
                        else:
                            print(f"Body Preview: {str(data)[:200]}...")
                    elif isinstance(data, list):
                        print(f"List Preview: {str(data)[:200]}...")
                    return True
                except Exception as e:
                    print(f"Response: Failed to parse JSON ({e})")
                    text = await response.text()
                    print(f"Raw Text: {text[:100]}...")
            else:
                print(f"Response: Error {status}")
                return False
    except Exception as e:
        print(f"Error: {e}")
        return False

async def main():
    print(f"Target Service: {BASE_URL}")
    print("Verifying EPIC-005 Endpoints...")
    
    # trust_env=False is critical to bypass container proxy settings
    async with aiohttp.ClientSession(trust_env=False) as session:
        
        # 1. Batch Real-time Quotes
        await test_endpoint(session, "Batch Real-time Quotes", f"{BASE_URL}/quotes/realtime?codes={TEST_BATCH_STOCKS}")
        
        # 2. Stock Liquidity Metrics
        await test_endpoint(session, "Stock Liquidity Metrics", f"{BASE_URL}/stocks/{TEST_STOCK}/liquidity")
        
        # 3. Stock Status Check
        await test_endpoint(session, "Stock Status Check", f"{BASE_URL}/stocks/{TEST_STOCK}/status")
        
        # 4. Fundamentals Facade
        await test_endpoint(session, "Fundamentals Facade", f"{BASE_URL}/stocks/{TEST_STOCK}/fundamentals")
        
        # 5. Enhanced Stock List (Checking first 5)
        await test_endpoint(session, "Enhanced Stock List", f"{BASE_URL}/stocks?limit=5")

if __name__ == "__main__":
    asyncio.run(main())

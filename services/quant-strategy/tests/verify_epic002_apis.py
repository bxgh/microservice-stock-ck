
import asyncio
import aiohttp
import sys
import os
import json
from urllib.parse import quote

# Configuration
BASE_URL = "http://127.0.0.1:8083/api/v1"
TEST_STOCK = "600519"
TEST_INDUSTRY = "酿酒行业"

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
                    # Print first few keys or summary to avoid massive output
                    print(f"Response: Success (Keys: {list(data.keys()) if isinstance(data, dict) else 'List'})")
                    # Check for standardized response format (success/data) if applicable, 
                    # but the doc showed direct JSON objects. Let's see what we get.
                    if isinstance(data, dict):
                        if 'data' in data:
                            print(f"Data Preview: {str(data['data'])[:200]}...")
                        else:
                            print(f"Body Preview: {str(data)[:200]}...")
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
    
    async with aiohttp.ClientSession(trust_env=False) as session:
        # 1. Financial Indicators
        await test_endpoint(session, "Financial Indicators", f"{BASE_URL}/finance/indicators/{TEST_STOCK}")
        
        # 2. Financial History
        await test_endpoint(session, "Financial History", f"{BASE_URL}/finance/history/{TEST_STOCK}?periods=2")
        
        # 3. Market Valuation
        await test_endpoint(session, "Current Valuation", f"{BASE_URL}/market/valuation/{TEST_STOCK}")
        
        # 4. Valuation History
        await test_endpoint(session, "Valuation History", f"{BASE_URL}/market/valuation/{TEST_STOCK}/history?years=1")
        
        # 5. Industry Stats
        # URL encode the chinese industry name
        industry_encoded = quote(TEST_INDUSTRY)
        await test_endpoint(session, "Industry Statistics", f"{BASE_URL}/finance/industry/{industry_encoded}/stats")
        
        # 6. Stock Detail (Enhanced)
        await test_endpoint(session, "Stock Detail (Enhanced)", f"{BASE_URL}/stocks/{TEST_STOCK}/detail")

if __name__ == "__main__":
    asyncio.run(main())

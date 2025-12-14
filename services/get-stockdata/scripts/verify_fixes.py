
import asyncio
import aiohttp
import sys
from urllib.parse import quote

BASE_URL = "http://localhost:8083/api/v1"

async def test_endpoint(session, name, url):
    print(f"\n[Test] {name}")
    print(f"URL: {url}")
    try:
        async with session.get(url) as response:
            status = response.status
            print(f"Status: {status}")
            if status == 200:
                print("✅ [PASS] Success")
                try:
                    data = await response.json()
                    # print(f"Data: {str(data)[:200]}...")
                except:
                    pass
                return True
            else:
                print(f"❌ [FAIL] Error {status}")
                text = await response.text()
                print(f"Response: {text[:200]}")
                return False
    except Exception as e:
        print(f"❌ [ERROR] Exception: {e}")
        return False

async def wait_for_service(session):
    ports = [8083, 8086]
    for i in range(20):
        for port in ports:
            url = f"http://localhost:{port}/api/v1/health"
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        print(f"✅ Service found independently on port {port}")
                        return f"http://localhost:{port}/api/v1"
            except:
                pass
        print(f"Waiting for service... ({i+1}/20)")
        await asyncio.sleep(1)
    return None

async def verify():
    async with aiohttp.ClientSession() as session:
        # Wait for service
        base_url = await wait_for_service(session)
        if not base_url:
            print("❌ Service failed to start or is unreachable on ports 8083/8086")
            return

        print(f"Verifying Fixes on {base_url}")
        
        # 1. Industry Stats
        industry_name = "酿酒行业"
        encoded_name = quote(industry_name)
        await test_endpoint(session, "Industry Stats (酿酒行业)", f"{base_url}/finance/industry/{encoded_name}/stats")

        # 2. Stocks Alias
        await test_endpoint(session, "Stocks List Alias (/stocks)", f"{base_url}/stocks?limit=5")

        # 3. Stock Detail
        await test_endpoint(session, "Stock Detail (600519)", f"{base_url}/stocks/600519/detail")

if __name__ == "__main__":
    asyncio.run(verify())

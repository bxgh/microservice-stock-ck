
import asyncio
import aiohttp
import sys

BASE_URL = "http://localhost:8083/api/v1"

async def test_endpoint(session, name, url):
    try:
        async with session.get(url) as response:
            status = response.status
            if status == 200:
                print(f"✅ [PASS] {name}: {url} -> 200 OK")
                return True
            elif status == 410:
                print(f"ℹ️ [GONE] {name}: {url} -> 410 (Deprecated, as expected)")
                return True
            else:
                print(f"❌ [FAIL] {name}: {url} -> {status}")
                text = await response.text()
                print(f"   Response: {text[:200]}")
                return False
    except Exception as e:
        print(f"❌ [ERROR] {name}: {url} -> {e}")
        return False

async def verify_all():
    print(f"--- Verifying All Data APIs on {BASE_URL} ---")
    
    async with aiohttp.ClientSession() as session:
        # EPIC-002 Financials
        await test_endpoint(session, "Financial Indicators", f"{BASE_URL}/finance/indicators/600519")
        await test_endpoint(session, "Financial History", f"{BASE_URL}/finance/history/600519")
        
        # EPIC-002 Valuation
        await test_endpoint(session, "Valuation Current", f"{BASE_URL}/market/valuation/600519")
        await test_endpoint(session, "Valuation History", f"{BASE_URL}/market/valuation/600519/history")
        
        # EPIC-002 Industry
        await test_endpoint(session, "Industry Stats", f"{BASE_URL}/market/industry/BK0477/stats") 
        
        # EPIC-005 Quotes
        await test_endpoint(session, "Realtime Quotes", f"{BASE_URL}/quotes/realtime?codes=600519")
        
        # EPIC-005 Liquidity
        await test_endpoint(session, "Liquidity", f"{BASE_URL}/stocks/600519/liquidity")
        
        # EPIC-005 Status & Fundamentals
        await test_endpoint(session, "Stock Status", f"{BASE_URL}/stocks/600519/status")
        await test_endpoint(session, "Fundamentals Facade", f"{BASE_URL}/stocks/600519/fundamentals")

if __name__ == "__main__":
    asyncio.run(verify_all())

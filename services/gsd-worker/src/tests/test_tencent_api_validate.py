import asyncio
import httpx
import os
import sys

# Cloud IP from config
CLOUD_HOST = "124.221.80.250"

REQUESTS = [
    # 1. K-Line (Baostock 8001)
    ("kline", f"http://{CLOUD_HOST}:8001/api/v1/history/kline/600519?start_date=2024-01-01&end_date=2024-01-10"),
    
    # 2. Financial (AkShare 8003)
    ("financial", f"http://{CLOUD_HOST}:8003/api/v1/finance/600519"),
    
    # 3. Valuation (AkShare 8003)
    # Note: Documentation says /api/v1/valuation/{code}
    ("valuation", f"http://{CLOUD_HOST}:8003/api/v1/valuation/600519"),
    
    # 4. Shareholder (AkShare 8003)
    ("shareholder", f"http://{CLOUD_HOST}:8003/api/v1/shareholder/600519"),
    
    # 5. Capital Flow (AkShare 8003)
    ("capital_flow", f"http://{CLOUD_HOST}:8003/api/v1/capital_flow/600519"),
    
    # 6. Dividend (AkShare 8003)
    ("dividend", f"http://{CLOUD_HOST}:8003/api/v1/dividend/600519"),
    
    # 7. Block Trade (AkShare 8003) - Additional check from table
    ("block_trade", f"http://{CLOUD_HOST}:8003/api/v1/block_trade/daily"),
    
    # 8. Margin (AkShare 8003) - Additional check from table
    ("margin", f"http://{CLOUD_HOST}:8003/api/v1/margin/600519"),
    
    # 9. Top List (AkShare 8003)
    ("top_list", f"http://{CLOUD_HOST}:8003/api/v1/dragon_tiger/daily?date=20240115")
]

async def test_url(client, name, url):
    try:
        print(f"Testing {name}: {url} ...", end=" ", flush=True)
        resp = await client.get(url, timeout=15.0)
        print(f"[{resp.status_code}]")
        if resp.status_code == 200:
            try:
                data = resp.json()
                sample = str(data)[:150].replace('\n', ' ')
                print(f"  -> Success: {sample}...")
                return True
            except Exception:
                print(f"  -> Invalid JSON: {resp.text[:100]}")
        else:
            print(f"  -> Error: {resp.text[:100]}")
    except Exception as e:
        print(f"[FAILED] {e}")
    return False

async def main():
    print(f"Proxy Settings: HTTP_PROXY={os.environ.get('HTTP_PROXY')}")
    
    async with httpx.AsyncClient(trust_env=True) as client:
        results = []
        for name, url in REQUESTS:
            res = await test_url(client, name, url)
            results.append((name, res))
    
    print("\nSummary:")
    for name, success in results:
        print(f"{name}: {'✅ OK' if success else '❌ FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())

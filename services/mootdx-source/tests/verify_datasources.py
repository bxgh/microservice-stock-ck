#!/usr/bin/env python3
"""
Quick verification script for mootdx-source data sources
测试 mootdx, easyquotation, akshare 数据源是否正常工作
"""
import asyncio
import sys
import os

# Add paths
sys.path.insert(0, '/home/bxgh/microservice-stock/services/mootdx-source/src')

async def test_mootdx():
    """测试 mootdx 实时行情"""
    print("\n=== Testing mootdx ===")
    try:
        from mootdx.quotes import Quotes
        
        loop = asyncio.get_event_loop()
        client = await loop.run_in_executor(
            None,
            lambda: Quotes.factory(market='std', server=('119.147.212.81', 7709))
        )
        
        data = await loop.run_in_executor(
            None,
            lambda: client.quotes(symbol=['000001', '600519'])
        )
        
        if data is not None and not data.empty:
            print(f"✓ mootdx: Got {len(data)} records")
            print(f"  Columns: {list(data.columns)[:5]}...")
            print(f"  Sample: code={data.iloc[0].get('code', 'N/A')}")
            return True
        else:
            print("✗ mootdx: Empty result")
            return False
    except Exception as e:
        print(f"✗ mootdx failed: {e}")
        return False


async def test_easyquotation():
    """测试 easyquotation 实时行情"""
    print("\n=== Testing easyquotation ===")
    try:
        import easyquotation
        
        loop = asyncio.get_event_loop()
        client = await loop.run_in_executor(
            None,
            lambda: easyquotation.use('sina')
        )
        
        data = await loop.run_in_executor(
            None,
            lambda: client.stocks(['000001', '600519'])
        )
        
        if data:
            print(f"✓ easyquotation: Got {len(data)} records")
            if '000001' in data:
                sample = data['000001']
                print(f"  Keys: {list(sample.keys())[:5]}...")
            return True
        else:
            print("✗ easyquotation: Empty result")
            return False
    except Exception as e:
        print(f"✗ easyquotation failed: {e}")
        return False


async def test_akshare():
    """测试 akshare 数据"""
    print("\n=== Testing akshare (via HTTP) ===")
    try:
        import aiohttp
        
        # 测试 akshare API
        akshare_url = os.getenv("AKSHARE_API_URL", "http://124.221.80.250:8000")
        endpoint = "/api/v1/rank/hot"  # 热门排行
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{akshare_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        print(f"✓ akshare: Got {len(data)} records")
                        return True
                    else:
                        print("✗ akshare: Empty result")
                        return False
                else:
                    print(f"✗ akshare: HTTP {resp.status}")
                    return False
    except asyncio.TimeoutError:
        print("✗ akshare: Timeout")
        return False
    except Exception as e:
        print(f"✗ akshare failed: {e}")
        return False


async def test_validation():
    """测试数据验证逻辑"""
    print("\n=== Testing validation logic ===")
    try:
        import pandas as pd
        from datasource_capabilities import DataSource, CAPABILITIES
        
        # 测试能力注册表
        print(f"✓ Capabilities registered for {len(CAPABILITIES)} sources")
        for src, cap in CAPABILITIES.items():
            print(f"  - {src.value}: {cap.supported_types}, reliability={cap.reliability}")
        
        return True
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        return False


async def main():
    print("=" * 50)
    print("MooTDX-Source Data Source Verification")
    print("=" * 50)
    
    results = {}
    
    # Run tests
    results['mootdx'] = await test_mootdx()
    results['easyquotation'] = await test_easyquotation()
    results['akshare'] = await test_akshare()
    results['validation'] = await test_validation()
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

#!/usr/bin/env python3
"""Quick verification of real data endpoints"""
import requests
import sys

BASE_URL = "http://127.0.0.1:8083"

def test_stock_list():
    print("Testing stock list endpoint...")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/stocks/list?limit=5", timeout=10)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Success: {data.get('success')}")
            print(f"  Count: {len(data.get('data', []))}")
            if data.get('data'):
                print(f"  Sample: {data['data'][0]}")
            return True
        else:
            print(f"  Error: {resp.text}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False

def test_valuation():
    print("\nTesting valuation endpoint...")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/finance/valuation/history/600519", timeout=10)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Success: {data.get('success')}")
            if isinstance(data.get('data'), list):
                print(f"  Records: {len(data['data'])}")
            return True
        else:
            print(f"  Error: {resp.text}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False

def test_health():
    print("\nTesting health endpoint...")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Response: {resp.json()}")
            return True
        return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Real Data Integration Verification")
    print("=" * 60)
    
    results = []
    results.append(("Health Check", test_health()))
    results.append(("Stock List", test_stock_list()))
    results.append(("Valuation Data", test_valuation()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)

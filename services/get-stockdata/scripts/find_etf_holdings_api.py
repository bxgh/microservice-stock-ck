#!/usr/bin/env python3
"""
Test various akshare ETF-related APIs to find the right one for holdings
"""
import sys
sys.path.insert(0, '/app/src')

import akshare as ak

print("="*60)
print("Testing Akshare ETF Holdings APIs")
print("="*60)

etf_code = "512760"  # 芯片ETF

# Try different APIs
apis_to_test = [
    ("fund_etf_fund_info_em", lambda: ak.fund_etf_fund_info_em(fund=etf_code)),
    ("fund_etf_hist_em", lambda: ak.fund_etf_hist_em(symbol=etf_code, period="daily", start_date="20241201", end_date="20241205")),
    ("fund_portfolio_hold_em", lambda: ak.fund_portfolio_hold_em(symbol=etf_code, date="2024")),
    ("fund_etf_category_sina", lambda: ak.fund_etf_category_sina(symbol="ETF基金")),
]

for api_name, api_func in apis_to_test:
    print(f"\n{'='*60}")
    print(f"Testing: ak.{api_name}()")
    print(f"{'='*60}")
    
    try:
        df = api_func()
        
        if df is not None and not df.empty:
            print(f"✅ Success! Got {len(df)} rows")
            print(f"\n🔍 Columns: {df.columns.tolist()}")
            print(f"\n📋 First 3 rows:")
            print(df.head(3).to_string())
        else:
            print(f"⚠️  Empty DataFrame")
            
    except TypeError as e:
        if "got an unexpected keyword argument" in str(e):
            print(f"⚠️  API signature changed or wrong parameters")
            print(f"   Error: {e}")
        else:
            raise
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)[:200]}")

print(f"\n{'='*60}")
print("Searching akshare documentation...")
print(f"{'='*60}")

# List all fund-related functions
import inspect
fund_funcs = [name for name in dir(ak) if 'fund' in name.lower() and 'etf' in name.lower()]
print(f"\nFound {len(fund_funcs)} fund/etf-related functions in akshare:")
for func in sorted(fund_funcs)[:20]:  # Show first 20
    print(f"  - {func}")

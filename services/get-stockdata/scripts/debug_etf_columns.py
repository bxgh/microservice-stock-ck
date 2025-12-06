#!/usr/bin/env python3
"""
Debug script to check akshare ETF API column names
"""
import sys
sys.path.insert(0, '/app/src')

import akshare as ak
import pandas as pd

# Test ETF codes from config
etf_codes = [
    ("512760", "芯片ETF"),
    ("512480", "半导体ETF"),
    ("159806", "新能源车ETF"),
    ("515790", "光伏ETF"),
    ("512290", "生物医药ETF"),
    ("512690", "白酒ETF"),
    ("512000", "券商ETF"),
    ("512800", "银行ETF"),
    ("512400", "有色金属ETF"),
]

print("="*60)
print("Akshare ETF API Column Name Inspection")
print("="*60)

for code, name in etf_codes:
    print(f"\n{'='*60}")
    print(f"Testing: {code} ({name})")
    print(f"{'='*60}")
    
    try:
        # Try primary method
        print(f"\n📊 Method 1: fund_etf_fund_info_em()")
        df = ak.fund_etf_fund_info_em(fund=code)
        
        if df is not None and not df.empty:
            print(f"✅ Success! Got {len(df)} rows")
            print(f"\n🔍 Column Names:")
            for i, col in enumerate(df.columns, 1):
                print(f"  {i}. '{col}'")
            
            print(f"\n📋 Sample Data (first 3 rows):")
            print(df.head(3).to_string())
            break  # Found one that works, stop here
        else:
            print(f"⚠️  Returned empty DataFrame")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)[:100]}")
    
    try:    
        # Try fallback method
        print(f"\n📊 Method 2: index_stock_cons() (fallback)")
        df_fallback = ak.index_stock_cons(symbol=code)
        
        if df_fallback is not None and not df_fallback.empty:
            print(f"✅ Fallback success! Got {len(df_fallback)} rows")
            print(f"\n🔍 Column Names:")
            for i, col in enumerate(df_fallback.columns, 1):
                print(f"  {i}. '{col}'")
            
            print(f"\n📋 Sample Data (first 3 rows):")
            print(df_fallback.head(3).to_string())
            break  # Found one that works, stop here
        else:
            print(f"⚠️  Returned empty DataFrame")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)[:100]}")

print(f"\n{'='*60}")
print("Debug Complete")
print(f"{'='*60}")

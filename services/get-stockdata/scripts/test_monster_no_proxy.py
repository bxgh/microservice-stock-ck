#!/usr/bin/env python3
"""
Test Monster Stocks WITHOUT proxy to isolate the issue
"""
import sys
sys.path.insert(0, '/app/src')

import os

# Temporarily clear proxy env vars
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        print(f"Clearing {key}={os.environ[key]}")
        del os.environ[key]

print("="*60)
print("Testing Monster Stocks WITHOUT Proxy")
print("="*60)

import akshare as ak

try:
    print("\n🎲 Fetching全市场实时行情 (no proxy)...")
    df = ak.stock_zh_a_spot_em()
    
    if df is not None and not df.empty:
        print(f"✅ Success! Got {len(df)} stocks")
        print(f"\n🔍 Columns: {df.columns.tolist()[:10]}...")
        print(f"\n📋 First 3 stocks:")
        print(df.head(3)[['代码', '名称', '涨跌幅', '换手率']].to_string())
        
        # Apply monster stock filters
        print(f"\n🔥 Applying monster stock filters:")
        print(f"   涨跌幅 > 9%")
        print(f"   换手率 > 10%")
        print(f"   流通市值 < 500亿")
        
        df_filtered = df[df['涨跌幅'] > 9.0]
        print(f"   After 涨跌幅 filter: {len(df_filtered)} stocks")
        
        df_filtered = df_filtered[df_filtered['换手率'] > 10.0]
        print(f"   After 换手率 filter: {len(df_filtered)} stocks")
        
        if '流通市值' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['流通市值'] < 50000000000]
            print(f"   After 流通市值 filter: {len(df_filtered)} stocks")
        
        if len(df_filtered) > 0:
            df_sorted = df_filtered.sort_values('涨跌幅', ascending=False)
            monsters = df_sorted.head(10)
            
            print(f"\n✅ Top 10 Monster Stocks:")
            print(monsters[['代码', '名称', '涨跌幅', '换手率']].to_string())
        else:
            print(f"\n⚠️  No stocks match the monster criteria today")
            
    else:
        print(f"❌ Returned empty DataFrame")
        
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)[:200]}")
    import traceback
    traceback.print_exc()

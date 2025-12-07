#!/usr/bin/env python3
"""
Verify Ranking APIs for Dynamic Promotion Strategy (Story 004.03)
We need APIs that can return 'Top Movers' or 'Rapid Risers' without scanning the whole market.
"""
import sys
sys.path.insert(0, '/app/src')
import akshare as ak
import pandas as pd
import time

def test_api(name, func, **kwargs):
    print(f"\nTesting {name}...")
    try:
        start = time.time()
        df = func(**kwargs)
        duration = time.time() - start
        
        if df is not None and not df.empty:
            print(f"✅ Success ({duration:.2f}s) - Got {len(df)} rows")
            print(f"   Columns: {df.columns.tolist()[:5]}...")
            print(df.head(3).to_string())
            return True
        else:
            print(f"⚠️  Returned empty result")
            return False
            
    except Exception as e:
        print(f"❌ Failed: {str(e)[:100]}")
        return False

print("="*60)
print("Verifying Ranking APIs for Dynamic Promotion")
print("="*60)

# 1. 盘中异动 (Rocketing / Rapid Change)
# This is ideal for "5 min change > 3%" detection
test_api("stock_changes_em (盘中异动)", ak.stock_changes_em, symbol="全部")

# 2. 人气榜 (Sentiment)
test_api("stock_hot_rank_em (人气榜)", ak.stock_hot_rank_em)

# 3. 飙升榜 (Soaring)
test_api("stock_hot_up_em (飙升榜)", ak.stock_hot_up_em)

# 4. 同花顺-涨速榜 (Generic Rank)
# Note: THS APIs might require cookies/js, testing just in case
try:
    test_api("stock_rank_xstp_ths (同花顺-向上突破)", ak.stock_rank_xstp_ths)
except:
    pass

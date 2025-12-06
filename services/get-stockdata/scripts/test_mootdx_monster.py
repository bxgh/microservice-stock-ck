#!/usr/bin/env python3
"""
Test if mootdx can be used for Monster Stocks detection
Check what fields are available in mootdx quotes
"""
import sys
sys.path.insert(0, '/app/src')

# Use the existing mootdx client from main.py
from mootdx.quotes import Quotes

print("="*60)
print("Testing Mootdx for Monster Stocks Detection")
print("="*60)

try:
    # Initialize same as main.py
    client = Quotes.factory(market='std', multithread=True, heartbeat=True)
    
    # Get list of all stocks
    print("\n1. Getting stock list...")
    stocks_sz = client.stocks(market=0)  # Shenzhen
    stocks_sh = client.stocks(market=1)  # Shanghai
    
    print(f"   SZ stocks: {len(stocks_sz)}")
    print(f"   SH stocks: {len(stocks_sh)}")
    
    # Get sample quotes to see available fields
    print("\n2. Getting sample quotes...")
    sample_codes = ['000001', '600000', '300059']
    quotes = client.quotes(symbol=sample_codes)
    
    print(f"\n3. Available columns in mootdx quotes:")
    print(f"   {quotes.columns.tolist()}")
    
    print(f"\n4. Sample data:")
    print(quotes.to_string())
    
    # Check if we have the needed fields for monster stock filtering
    print(f"\n5. Monster Stock Filter Requirements:")
    required_fields = {
        '涨跌幅': 'change' or similar,
        '换手率': 'turnover' or similar,
        '流通市值': 'market_cap' or similar
    }
    
    print(f"   Checking for required fields...")
    for cn_name, possible_names in [
        ('涨跌幅', ['change', 'pct_change', 'change_pct']),
        ('换手率', ['turnover', 'turnover_rate']),
        ('流通市值', ['market_cap', 'circulating_market_cap', 'float_market_cap'])
    ]:
        found = any(field in quotes.columns for field in possible_names)
        print(f"   {cn_name}: {'✅ Found' if found else '❌ Not found'}")
        if found:
            matching = [f for f in possible_names if f in quotes.columns]
            print(f"      → Column: {matching}")
    
    print(f"\n6. Conclusion:")
    # Calculate if we can derive needed fields
    if 'price' in quotes.columns and 'last_close' in quotes.columns:
        print(f"   ✅ Can calculate 涨跌幅 from price/last_close")
    if 'vol' in quotes.columns:
        print(f"   ⚠️ Have volume, but need total shares for 换手率")
    
    print(f"\n✅ Test complete!")
    
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

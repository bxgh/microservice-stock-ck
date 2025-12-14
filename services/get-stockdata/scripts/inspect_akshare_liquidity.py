
import akshare as ak
import pandas as pd
import traceback

def check_liquidity_data():
    print("--- Checking Liquidity Data ---")
    
    # 1. Realtime Quotes (Batch)
    print("\n1. stock_zh_a_spot_em (Batch Realtime)...")
    try:
        df = ak.stock_zh_a_spot_em()
        print("Columns:", df.columns.tolist())
        print(df.head(1))
        # Check for bid/ask or volume
    except Exception:
        traceback.print_exc()

    # 2. Bid/Ask / Order Book
    print("\n2. Checking for Bid/Ask APIs...")
    # There isn't a direct "stock_bid_ask_em". 
    # Usually real-time L1 (5 levels) is available via individual stock quote APIs
    # Let's try stock_individual_info_em again to see if it has 5-level 
    # or look for 'stock_zh_a_tick_tx_js' (Tencent) or similar
    
    try:
        # Sina L1 is often used for 5-level
        # But AkShare might wrap it. 
        # stock_zh_a_spot_em usually only has latest price, not 5 levels.
        pass
    except Exception:
        pass

if __name__ == "__main__":
    check_liquidity_data()

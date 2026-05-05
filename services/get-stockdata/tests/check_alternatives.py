
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlternativesCheck")

def check_mootdx():
    print("\n--- Checking Mootdx (Std) ---")
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market='std')
        print("✅ Mootdx Quotes initialized")
        
        # Try to get index list or something similar?
        # Mootdx focuses on quotes, maybe not industry list directly.
        # But let's check if we can get basic info
        print("Attempting to get stock count from Shanghai...")
        # basic functionality test
        data = client.stocks(market=1) # 1 for SH?
        if data is not None and not data.empty:
            print(f"✅ Mootdx fetch success. Rows: {len(data)}")
            print(data.head())
        else:
            print("⚠️ Mootdx returned empty data")
            
    except Exception as e:
        print(f"❌ Mootdx error: {e}")

def check_qstock():
    print("\n--- Checking QStock ---")
    try:
        import qstock as qs
        print("✅ QStock imported")
        
        # QStock wraps many sources, including EastMoney (might have same proxy issue)
        # But it also wraps others.
        
        # Check industry list
        print("Attempting to fetch industry list (qs.industry_list)...")
        try:
           # Note: Function names might vary, QStock has many
           df = qs.realtime_data('行业') # Try to get industry realtime quotes?
           if df is not None and not df.empty:
               print(f"✅ QStock industry fetch success. Rows: {len(df)}")
               print(df.head())
           else:
               print("⚠️ QStock returned empty industry data")
        except Exception as e:
            print(f"❌ QStock industry fetch failed: {e}")

    except ImportError:
        print("❌ QStock not installed")
    except Exception as e:
        print(f"❌ QStock error: {e}")

if __name__ == "__main__":
    check_mootdx()
    check_qstock()

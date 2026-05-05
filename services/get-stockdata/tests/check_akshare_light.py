import akshare as ak
import os

def check_akshare_light():
    print(f"Proxy Config: {os.environ.get('http_proxy')}")
    try:
        print("Fetching stock_individual_info_em(600519)...")
        df = ak.stock_individual_info_em(symbol="600519")
        
        if df is None or df.empty:
            print("❌ DataFrame is empty or None")
        else:
            print(f"✅ Fetch Success. Shape: {df.shape}")
            print(df)
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    check_akshare_light()

import akshare as ak
import pandas as pd

def check_akshare_spot():
    try:
        print("Fetching stock_zh_a_spot_em...")
        df = ak.stock_zh_a_spot_em()
        
        if df is None or df.empty:
            print("❌ DataFrame is empty or None")
        else:
            print(f"✅ Fetch Success. Shape: {df.shape}")
            print("Columns:", df.columns.tolist())
            
            # Check for industry column candidates
            candidates = ['行业', '所属行业', '板块']
            found = [col for col in candidates if col in df.columns]
            print(f"Industry candidates found: {found}")
            
            if not found:
                 print("⚠️ No industry column found in spot data!")
            
            # Check for PE/PB
            pe_candidates = ['市盈率-动态', '市盈率']
            pe_found = [col for col in pe_candidates if col in df.columns]
            print(f"PE candidates found: {pe_found}")
            
            if '市净率' in df.columns:
                print("✅ PB column found")
            else:
                print("⚠️ PB column missing")
                
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    check_akshare_spot()


import logging
import os
# Ensure node path if needed, though docker should have it
# os.environ['PATH'] += ":/path/to/node"

def check_pywencai():
    print("\n--- Checking Pywencai ---")
    try:
        import pywencai
        print("✅ Pywencai imported")
        
        # Test Query: Industry List / Constituents
        # Querying for "components of Alcoholic Industry" essentially
        query = "酿酒行业成分股"
        print(f"Querying: {query}")
        
        res = pywencai.get(query=query, perpage=30)
        
        if res is not None and not res.empty:
            print(f"✅ Pywencai fetch success. Rows: {len(res)}")
            print("Columns:", res.columns.tolist())
            print(res.head(3))
            
            # Check for PE/PB columns (dynamic names usually)
            # Wencai usually returns fields like '市盈率(pe)', '市净率(pb)'
            pe_cols = [c for c in res.columns if '市盈率' in c]
            pb_cols = [c for c in res.columns if '市净率' in c]
            print(f"Found PE cols: {pe_cols}")
            print(f"Found PB cols: {pb_cols}")
        else:
            print("⚠️ Pywencai returned empty results")
            
    except Exception as e:
        print(f"❌ Pywencai error: {e}")

if __name__ == "__main__":
    check_pywencai()

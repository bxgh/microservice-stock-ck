
import akshare as ak
import pandas as pd

def test_stock_info():
    print("Testing stock_individual_info_em...")
    try:
        df = ak.stock_individual_info_em(symbol="600519")
        print("Columns:", df.columns.tolist())
        print("Data preview:")
        print(df)
        
        # Check for specific fields
        info_dict = dict(zip(df['item'], df['value']))
        print("\nExtracted Info:")
        print(f"Industry: {info_dict.get('行业')}")
        print(f"Listing Date: {info_dict.get('上市时间')}")
        print(f"Total Shares: {info_dict.get('总股本')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_stock_info()

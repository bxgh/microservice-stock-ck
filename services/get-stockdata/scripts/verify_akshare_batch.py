
import akshare as ak
import pandas as pd
from datetime import datetime

def test_batch_api():
    print("Testing stock_yjbb_em (Performance Report)...")
    try:
        # Get latest reporting period (approximate)
        # Usually format is YYYYMMDD, e.g., 20240930
        # Let's try to get the most recent one dynamically or hardcode a recent one known to exist
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Simple logic to guess a valid report date
        if current_month < 4:
            report_date = f"{current_year-1}0930" # Q3 prev year
        elif current_month < 8:
            report_date = f"{current_year}0331" # Q1
        elif current_month < 10:
            report_date = f"{current_year}0630" # Q2
        else:
            report_date = f"{current_year}0930" # Q3
            
        print(f"Fetching for date: {report_date}")
        df = ak.stock_yjbb_em(date=report_date)
        
        if df is not None and not df.empty:
            print("✅ Success!")
            print(f"Columns: {df.columns.tolist()}")
            print(f"Rows: {len(df)}")
            print("\nPreview:")
            print(df[['股票代码', '净资产收益率', '营业收入-同比增长']].head())
            return True
        else:
            print("❌ Empty result")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_batch_api()

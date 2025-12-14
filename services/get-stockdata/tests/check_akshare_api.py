import akshare as ak
from datetime import datetime
import pandas as pd

def check_akshare_financial():
    # Logic from IndustryService
    curr_month = datetime.now().month
    curr_year = datetime.now().year
    
    # Logic copied from get_industry_stats
    if curr_month < 4: report_date = f"{curr_year-1}0930"
    elif curr_month < 8: report_date = f"{curr_year}0331"
    elif curr_month < 10: report_date = f"{curr_year}0630"
    else: report_date = f"{curr_year}0930"
    
    print(f"Calculated Report Date: {report_date}")
    
    try:
        print(f"Fetching stock_yjbb_em for date {report_date}...")
        df = ak.stock_yjbb_em(date=report_date)
        
        if df is None or df.empty:
            print("❌ DataFrame is empty or None")
        else:
            print(f"✅ Fetch Success. Shape: {df.shape}")
            print("Columns:", df.columns.tolist())
            
            # Check required columns
            required = ['股票代码', '净资产收益率', '营业总收入-同比增长']
            missing = [col for col in required if col not in df.columns]
            if missing:
                print(f"❌ Missing columns: {missing}")
            else:
                print("✅ Required columns present")
                
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    check_akshare_financial()

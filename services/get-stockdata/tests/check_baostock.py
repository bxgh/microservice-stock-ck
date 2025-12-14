
import baostock as bs
import pandas as pd
import datetime

def check_baostock():
    print("--- Checking Baostock ---")
    
    lg = bs.login()
    print(f"Login respond error_code: {lg.error_code}")
    print(f"Login respond  error_msg: {lg.error_msg}")
    
    if lg.error_code != '0':
        print("❌ Login failed")
        return

    # Check Industry Data
    try:
        print("Querying stock_industry ...")
        # Get industry for a few stocks or all
        rs = bs.query_stock_industry()
        print(f"query_stock_industry error_code: {rs.error_code}")
        
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())
            # if len(data_list) > 5: break # Removed limit
            
        if data_list:
            df = pd.DataFrame(data_list, columns=rs.fields)
        if data_list:
            df = pd.DataFrame(data_list, columns=rs.fields)
            print("✅ Industry Data Loaded. Shape:", df.shape)
            if 'industry' in df.columns:
                unique_industries = df['industry'].unique()
                print(f"Unique Industries ({len(unique_industries)}):")
                print(unique_industries[:50]) # Print first 50
                # Check for our target
                if "酿酒行业" in unique_industries:
                    print("✅ Found '酿酒行业'")
                else:
                    print("❌ '酿酒行业' NOT found. Closest matches:")
                    print([x for x in unique_industries if "酒" in str(x)])
            else:
                print("⚠️ Column 'industry' not found in response")
                print("Columns:", df.columns)
        else:
             print("⚠️ No data returned")

        # Check PE/PB Data?
        # Baostock has query_history_k_data_plus which includes peTTM, pbMRQ
        print("Querying PE/PB for 600519 ...")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        start = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        rs = bs.query_history_k_data_plus(
            "sh.600519",
            "date,code,close,peTTM,pbMRQ",
            start_date=start, end_date=today,
            frequency="d"
        )
        data_list = []
        while (rs.error_code == '0') and rs.next():
             data_list.append(rs.get_row_data())
             
        if data_list:
            df = pd.DataFrame(data_list, columns=rs.fields)
            print("✅ PE/PB Data Sample:")
            print(df)
        else:
            print("⚠️ No PE/PB data")

    except Exception as e:
        print(f"❌ Exception: {e}")
    finally:
        bs.logout()

if __name__ == "__main__":
    check_baostock()

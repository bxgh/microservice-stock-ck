import akshare as ak
import pandas as pd
import time

def test_akshare_snapshot():
    print(f"AkShare version: {ak.__version__}")
    
    symbol = "sh600000" # 浦发银行
    print(f"Testing snapshot for {symbol}...")
    
    try:
        # 尝试获取新浪行情
        # stock_zh_a_spot_em 是东方财富的实时行情，可能没有盘口
        # stock_zh_a_spot_sina 是新浪的实时行情，通常有盘口
        
        print("Fetching Sina real-time data...")
        # 注意：akshare接口经常变动，这里尝试几个可能的接口
        
        # 接口1: stock_zh_a_spot_em (东方财富)
        # df_em = ak.stock_zh_a_spot_em()
        # print("EM data columns:", df_em.columns)
        
        # 接口2: stock_bid_ask_em (东方财富买卖盘) - 如果有的话
        
        # 接口3: stock_zh_a_spot (新浪) - 旧版接口，可能已废弃
        
        # 直接尝试获取个股的详细信息
        # stock_individual_info_em
        
        # 让我们尝试获取实时行情并打印列名，看是否有 bid1, ask1
        df = ak.stock_zh_a_spot_em()
        # 过滤出浦发银行
        row = df[df['代码'] == '600000']
        if not row.empty:
            print("EM Data for 600000:")
            print(row.iloc[0])
        else:
            print("600000 not found in EM spot data")
            
        # 尝试新浪接口，通常新浪接口包含买一卖一
        # akshare中新浪接口可能是 stock_zh_a_spot
        try:
            df_sina = ak.stock_zh_a_spot()
            print("Sina data columns:", df_sina.columns)
            # 尝试查找浦发银行
            # 通常新浪接口返回的代码可能是 'sh600000' 或 '600000'
            # 让我们打印前几行看看结构
            print("First 2 rows of Sina data:")
            print(df_sina.head(2))
            
            # 尝试更智能的过滤
            mask = df_sina.astype(str).apply(lambda x: x.str.contains('600000')).any(axis=1)
            if mask.any():
                print("\nFound 600000 in Sina data:")
                print(df_sina[mask].iloc[0])
            else:
                print("sh600000 not found in Sina spot data")
        except Exception as e:
            print(f"Sina interface failed: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_akshare_snapshot()

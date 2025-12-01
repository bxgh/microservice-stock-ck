from mootdx.quotes import Quotes
import pandas as pd

def test_mootdx_snapshot():
    print("Testing Mootdx Snapshot...")
    
    try:
        client = Quotes.factory(market='std', multithread=True, heartbeat=True)
        print("Connected to Mootdx")
        
        # 获取浦发银行(600000)的行情快照
        # 市场代码: 0-深圳, 1-上海
        # 600000 是上海
        symbol = '600000'
        
        # quotes方法通常接受 list of symbols
        # 这里的symbol格式可能需要注意，有些接口需要带市场前缀，mootdx通常是直接传代码，然后指定市场？
        # 或者 quotes(symbol=['600000'])
        
        print(f"Fetching quotes for {symbol}...")
        df = client.quotes(symbol=[symbol])
        
        if df is not None and not df.empty:
            print("Mootdx Quotes Data:")
            print(df.iloc[0])
            print("\nColumns:", df.columns)
            
            # 检查是否有买一卖一
            required_cols = ['ask1', 'bid1', 'ask_vol1', 'bid_vol1']
            present = [col for col in required_cols if col in df.columns]
            print(f"Found required columns: {present}")
        else:
            print("No data returned")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mootdx_snapshot()

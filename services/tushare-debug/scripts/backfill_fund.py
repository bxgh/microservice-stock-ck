import os
import tushare as ts
import pandas as pd
from clickhouse_driver import Client
from dotenv import load_dotenv
from datetime import datetime
import time

# 加载配置
load_dotenv("/app/.env.tushare")

# 配置代理
os.environ["http_proxy"] = "http://192.168.151.18:3128"
os.environ["https_proxy"] = "http://192.168.151.18:3128"

def backfill_fund():
    """
    回补护盘核心基金数据 (VOL-06)
    """
    token = os.getenv("TUSHARE_TOKEN")
    ts.set_token(token)
    pro = ts.pro_api()
    
    ch_client = Client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
        user=os.getenv("CLICKHOUSE_USER", "admin"),
        password=os.getenv("CLICKHOUSE_PASSWORD", "admin123"),
        database="stock_data"
    )

    # 核心护盘 ETF (510300)
    fund_codes = ["510300.SH"]
    start_date = "20240101"
    end_date = datetime.now().strftime("%Y%m%d")
    
    print(f"🚀 开始回补基金数据: {fund_codes} 从 {start_date}")

    for ts_code in fund_codes:
        print(f"正在获取 {ts_code} 历史行情...")
        try:
            df = pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df.empty:
                print(f"⚠️ {ts_code} 无数据")
                continue
            
            # 数据格式化
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            # Tushare amount 单位是 千元
            df['amount'] = df['amount'] * 1000
            
            # 准备 ClickHouse 数据 (对齐 schema: stock_code, trade_date, open_price, high_price, low_price, close_price, volume, amount)
            # 注意: 这里借用 stock_kline_daily 存 ETF 也可以，或者存 fund_daily
            # 由于目前 ClickHouse 系统中已存在 stock_kline_daily，我们先存入这里便于聚合
            data = []
            for _, row in df.iterrows():
                data.append((
                    ts_code,
                    row['trade_date'],
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['vol']),
                    float(row['amount'])
                ))
            
            # 写入 ClickHouse
            print(f"写入 ClickHouse ({len(data)} 条)...")
            ch_client.execute(
                "INSERT INTO stock_kline_daily (stock_code, trade_date, open_price, high_price, low_price, close_price, volume, amount) VALUES",
                data
            )
            print(f"✅ {ts_code} 回补完成")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ {ts_code} 执行失败: {e}")

if __name__ == "__main__":
    backfill_fund()

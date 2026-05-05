import os
import tushare as ts
import pandas as pd
from clickhouse_driver import Client
from dotenv import load_dotenv
from datetime import datetime, date
import time

# 加载配置
load_dotenv("/app/.env.tushare")

# 配置代理
os.environ["http_proxy"] = "http://192.168.151.18:3128"
os.environ["https_proxy"] = "http://192.168.151.18:3128"

def backfill_rates():
    """
    回补回购利率数据 (VOL-05)
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

    start_date = "20240101"
    end_date = datetime.now().strftime("%Y%m%d")
    
    print(f"🚀 开始回补利率数据 (R007/FR007)，起始日期: {start_date}")

    # 需要获取的品种 (R007等)
    repo_codes = ["R001.IB", "R007.IB", "DR001.IB", "DR007.IB"]

    # 获取交易日列表 (银行间市场通常是周一至周五)
    cal = pro.trade_cal(exchange='SSE', is_open='1', start_date=start_date, end_date=end_date)
    trade_dates = sorted(cal['cal_date'].tolist())

    for date_str in trade_dates:
        # 转换为 datetime.date 对象以兼容 clickhouse-driver
        dt_date = datetime.strptime(date_str, "%Y%m%d").date()
        print(f"正在获取 {date_str} 利率数据...")
        try:
            # 使用 repo_daily 获取指定日期的所有品种
            df = pro.repo_daily(trade_date=date_str)
            if df.empty:
                continue
            
            # 过滤需要的品种
            df = df[df['ts_code'].isin(repo_codes)]
            if df.empty:
                continue

            # 数据格式化
            # ClickHouse schema: trade_date, repo_code, repo_name, close_rate, high_rate, low_rate, avg_rate, volume
            data = []
            for _, row in df.iterrows():
                # Tushare repo_daily 字段名: ts_code, close, high, low, weight (加权价通常指avg), amount (成交金额)
                data.append((
                    dt_date,
                    row['ts_code'],
                    row['ts_code'], # repo_name 这里直接存代码或留空
                    float(row['close']) if pd.notna(row['close']) else 0.0,
                    float(row['high']) if pd.notna(row['high']) else 0.0,
                    float(row['low']) if pd.notna(row['low']) else 0.0,
                    float(row['weight']) if pd.notna(row['weight']) else 0.0,
                    float(row['amount']) if pd.notna(row['amount']) else 0.0
                ))
            
            # 批量写入
            ch_client.execute(
                "INSERT INTO stock_repo_rates_local (trade_date, repo_code, repo_name, close_rate, high_rate, low_rate, avg_rate, volume) VALUES",
                data
            )
            print(f"   ✅ {date_str} 写入 {len(data)} 条")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ {date_str} 失败: {e}")
            time.sleep(2)

if __name__ == "__main__":
    backfill_rates()

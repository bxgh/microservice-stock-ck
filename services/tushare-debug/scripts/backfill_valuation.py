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

def backfill_valuation():
    """
    回补个股估值与流动性数据 (VOL-03/04)
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
    
    print(f"🚀 开始回补个股估值数据，起始日期: {start_date}")

    # 获取交易日列表
    cal = pro.trade_cal(exchange='SSE', is_open='1', start_date=start_date, end_date=end_date)
    trade_dates = sorted(cal['cal_date'].tolist())
    
    print(f"共计 {len(trade_dates)} 个交易日待回补 (正序)")

    for date_str in trade_dates:
        # 转换为 datetime.date 对象以兼容 clickhouse-driver
        dt_date = datetime.strptime(date_str, "%Y%m%d").date()
        
        # 检查是否已存在 (简单逻辑：如果记录数明显不足则回补)
        count = ch_client.execute(f"SELECT count() FROM stock_valuation_local WHERE trade_date = '{dt_date}'")[0][0]
        if count > 4000:
            print(f"⏩ {date_str} 已存在 ({count} 条记录)，跳过")
            continue

        print(f"正在获取 {date_str} 的全市场估值数据...")
        try:
            df = pro.daily_basic(trade_date=date_str)
            if df.empty:
                print(f"⚠️ {date_str} 无数据")
                continue
            
            # 数据格式化
            # ClickHouse schema: stock_code, trade_date, turnover_rate, pe, pb, ps, market_cap (total_mv), circ_mv, price (close)
            data = []
            for _, row in df.iterrows():
                # 剔除北交所 (视需求而定，文档中有些地方说过滤北证)
                if row['ts_code'].endswith('.BJ'):
                    continue
                    
                data.append((
                    row['ts_code'],
                    dt_date,
                    float(row['turnover_rate']) if pd.notna(row['turnover_rate']) else 0.0,
                    float(row['pe']) if pd.notna(row['pe']) else 0.0,
                    float(row['pb']) if pd.notna(row['pb']) else 0.0,
                    float(row['ps']) if pd.notna(row['ps']) else 0.0,
                    float(row['total_mv']) if pd.notna(row['total_mv']) else 0.0,
                    float(row['circ_mv']) if pd.notna(row['circ_mv']) else 0.0,
                    float(row['close']) if pd.notna(row['close']) else 0.0
                ))
            
            # 批量写入
            ch_client.execute(
                "INSERT INTO stock_valuation_local (stock_code, trade_date, turnover_rate, pe, pb, ps, market_cap, circ_mv, price) VALUES",
                data
            )
            print(f"✅ {date_str} 写入成功 ({len(data)} 条)")
            
            # 配合 Tushare 每分钟 200/500 次调用限制
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ {date_str} 执行失败: {e}")
            time.sleep(5)

if __name__ == "__main__":
    backfill_valuation()

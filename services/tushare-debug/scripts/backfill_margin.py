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

def backfill_margin():
    """
    回补融资融券数据 (VOL-02)
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
    
    print(f"🚀 开始回补融资融券数据，起始日期: {start_date}")

    # 获取交易日列表
    cal = pro.trade_cal(exchange='SSE', is_open='1', start_date=start_date, end_date=end_date)
    trade_dates = sorted(cal['cal_date'].tolist())
    
    print(f"共计 {len(trade_dates)} 个交易日待回补 (正序)")

    for date_str in trade_dates:
        # 转换为 datetime.date 对象以兼容 clickhouse-driver
        dt_date = datetime.strptime(date_str, "%Y%m%d").date()
        print(f"🔍 检查 {date_str}...", end='\r')
        
        # 检查是否已存在
        try:
            query = f"SELECT count() FROM stock_margin_local WHERE trade_date = '{dt_date}'"
            count = ch_client.execute(query)[0][0]
            if count > 2000:
                print(f"⏩ {date_str} 已存在 ({count} 条记录)，跳过")
                continue
        except Exception as e:
            print(f"❌ 检查 {date_str} 失败: {e}")
            break

        print(f"正在获取 {date_str} 的融资融券明细...")
        try:
            # margin_detail 接口获取全市场日度明细
            df = pro.margin_detail(trade_date=date_str)
            if df.empty:
                print(f"⚠️ {date_str} 无数据")
                continue
            
            # 数据格式化
            # ClickHouse schema: stock_code, trade_date, rz_balance, rq_balance, rz_buy, rz_repay, rq_sell, rq_repay
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['ts_code'],
                    dt_date,
                    float(row['rzye']) if pd.notna(row['rzye']) else 0.0,
                    float(row['rqye']) if pd.notna(row['rqye']) else 0.0,
                    float(row['rzmre']) if pd.notna(row['rzmre']) else 0.0,
                    float(row['rzche']) if pd.notna(row['rzche']) else 0.0,
                    float(row['rqmcl']) if pd.notna(row['rqmcl']) else 0.0,
                    float(row['rqchl']) if pd.notna(row['rqchl']) else 0.0
                ))
            
            # 批量写入
            ch_client.execute(
                "INSERT INTO stock_margin_local (stock_code, trade_date, rz_balance, rq_balance, rz_buy, rz_repay, rq_sell, rq_repay) VALUES",
                data
            )
            print(f"✅ {date_str} 写入成功 ({len(data)} 条)")
            
            # 频率控制
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ {date_str} 执行失败: {e}")
            time.sleep(5)

if __name__ == "__main__":
    backfill_margin()

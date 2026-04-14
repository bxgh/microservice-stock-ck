import os
import tushare as ts
import pandas as pd
from clickhouse_driver import Client
from dotenv import load_dotenv
from datetime import datetime

# 加载配置
load_dotenv("/app/.env.tushare")

# 配置代理
PROXY_URL = "http://192.168.151.18:3128"
os.environ["http_proxy"] = PROXY_URL
os.environ["https_proxy"] = PROXY_URL

def audit_vol_02_margin():
    """
    核对两融数据 (VOL-02)
    对比 ClickHouse(及 MySQL 镜像)与 Tushare
    """
    # 1. 准备连接
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

    # 2. 设置核对范围 (由于两融数据量大，选取最近一个月进行核对)
    start_date = "20260301"
    end_date = "20260401"
    
    print(f"🚀 开始审计 VOL-02 两融数据 [{start_date} -> {end_date}]")
    
    # 获取全市场合计的融资买入额情况 (ClickHouse)
    # 计算公式: SUM(rz_buy) per day
    try:
        query = f"SELECT trade_date, sum(rz_buy) as total_rz_buy FROM stock_margin WHERE trade_date >= '2026-03-01' AND trade_date <= '2026-04-01' GROUP BY trade_date ORDER BY trade_date"
        rows = ch_client.execute(query)
        df_ch = pd.DataFrame(rows, columns=['trade_date', 'total_rz_buy'])
        df_ch = df_ch.set_index('trade_date').sort_index()
    except Exception as e:
        print(f"❌ 无法从 ClickHouse 获取数据: {e}")
        return

    # 获取 Tushare 融资融券汇总数据 (Market level)
    try:
        # Tushare pro.margin 接口获取市场汇总
        df_ts = pro.margin(start_date=start_date, end_date=end_date, exchange_id='')
        # 汇总所有交易所 (SSE + SZSE)
        df_ts = df_ts.groupby('trade_date').agg({'rzbuy': 'sum'}).sort_index()
        df_ts.index = pd.to_datetime(df_ts.index).date
    except Exception as e:
        print(f"❌ 无法从 Tushare 获取数据: {e}")
        return

    # 对比汇总值
    comparison = df_ts.join(df_ch, lsuffix='_ts', rsuffix='_ch', how='outer')
    comparison['diff'] = (comparison['rzbuy'] - comparison['total_rz_buy']).abs()
    comparison['diff_pct'] = (comparison['diff'] / comparison['rzbuy']).fillna(0)

    print(f"\n汇总核对结果 (2026-03):")
    print(f"   - Tushare 有效天数: {len(df_ts)}")
    print(f"   - ClickHouse 有效天数: {len(df_ch)}")
    
    mismatch = comparison[comparison['diff_pct'] > 0.05] # 允许 5% 差异，通常由于统计口径或个别股票遗漏
    missing_ch = comparison[comparison['total_rz_buy'].isna()]
    
    print(f"   - 缺失(CH): {len(missing_ch)} 天")
    print(f"   - 显著差异 (>5%): {len(mismatch)} 天")
    
    if len(mismatch) > 0:
        print("\n详细差异样本 (前 5 条):")
        print(mismatch.head())

if __name__ == "__main__":
    audit_vol_02_margin()

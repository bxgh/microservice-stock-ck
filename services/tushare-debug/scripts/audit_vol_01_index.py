import os
import tushare as ts
import pandas as pd
from clickhouse_driver import Client
from dotenv import load_dotenv
from datetime import datetime

# 加载配置
load_dotenv("/app/.env.tushare")

# 配置代理 (如果需要)
PROXY_URL = "http://192.168.151.18:3128"
os.environ["http_proxy"] = PROXY_URL
os.environ["https_proxy"] = PROXY_URL

def audit_vol_01_index():
    """
    核对指数成交额数据 (VOL-01)
    对比 ClickHouse (现有) 与 Tushare (原始源)
    """
    # 1. 初始化 Tushare
    token = os.getenv("TUSHARE_TOKEN")
    ts.set_token(token)
    pro = ts.pro_api()
    
    # 2. 初始化 ClickHouse
    ch_client = Client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
        user=os.getenv("CLICKHOUSE_USER", "admin"),
        password=os.getenv("CLICKHOUSE_PASSWORD", "admin123"),
        database="stock_data"
    )

    # 3. 设置核对范围 (2024年至今)
    start_date = "20240101"
    end_date = datetime.now().strftime("%Y%m%d")
    
    print(f"🚀 开始审计 VOL-01 指数成交额数据 [{start_date} -> {end_date}]")
    
    indices = {
        "000001.SH": "上证指数",
        "399106.SZ": "深证综指"
    }
    
    report = []

    for ts_code, name in indices.items():
        print(f"\n检查 {name} ({ts_code})...")
        
        # A. 从 Tushare 获取数据
        try:
            df_ts = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            # Tushare amount 单位是 千元，需转为元以对齐
            df_ts['amount'] = df_ts['amount'] * 1000
            df_ts['trade_date'] = pd.to_datetime(df_ts['trade_date']).dt.date
            df_ts = df_ts[['trade_date', 'amount']].set_index('trade_date').sort_index()
        except Exception as e:
            print(f"❌ 无法从 Tushare 获取 {ts_code}: {e}")
            continue

        # B. 从 ClickHouse 获取数据
        try:
            query = f"SELECT trade_date, amount FROM stock_kline_daily WHERE stock_code = '{ts_code}' AND trade_date >= '2024-01-01'"
            rows = ch_client.execute(query)
            df_ch = pd.DataFrame(rows, columns=['trade_date', 'amount'])
            df_ch = df_ch.set_index('trade_date').sort_index()
        except Exception as e:
            print(f"❌ 无法从 ClickHouse 获取 {ts_code}: {e}")
            continue

        # C. 合并对比
        comparison = df_ts.join(df_ch, lsuffix='_ts', rsuffix='_ch', how='outer')
        comparison['diff'] = (comparison['amount_ts'] - comparison['amount_ch']).abs()
        comparison['diff_pct'] = (comparison['diff'] / comparison['amount_ts']).fillna(0)
        
        # D. 统计
        mismatch = comparison[comparison['diff_pct'] > 0.001] # 允许 0.1% 误差（可能的舍入不同）
        missing_ch = comparison[comparison['amount_ch'].isna()]
        missing_ts = comparison[comparison['amount_ts'].isna()]
        
        print(f"   - Tushare 样本数: {len(df_ts)}")
        print(f"   - ClickHouse 样本数: {len(df_ch)}")
        print(f"   - 缺失(CH): {len(missing_ch)} 天")
        print(f"   - 显著差异 (>0.1%): {len(mismatch)} 天")
        
        report.append({
            "code": ts_code,
            "name": name,
            "ts_count": len(df_ts),
            "ch_count": len(df_ch),
            "missing_ch": len(missing_ch),
            "mismatch": len(mismatch)
        })

    print("\n" + "="*50)
    print("审计汇总报告 (VOL-01)")
    print("="*50)
    for r in report:
        status = "✅ 优" if r['missing_ch'] == 0 and r['mismatch'] == 0 else "⚠️ 需检查"
        print(f"{r['name']} ({r['code']}): {status}")
        print(f"   [CH缺失: {r['missing_ch']}] [差异数: {r['mismatch']}]")

if __name__ == "__main__":
    audit_vol_01_index()

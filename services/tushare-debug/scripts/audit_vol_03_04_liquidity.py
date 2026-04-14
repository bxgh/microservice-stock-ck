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

def audit_vol_03_04_liquidity():
    """
    核对流动性与估值数据 (VOL-03, VOL-04)
    对比 ClickHouse 与 Tushare
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

    # 2. 选取最近一个交易日进行全市场核对
    # 获取 ClickHouse 中最近的一天
    try:
        query = "SELECT max(trade_date) FROM stock_valuation_local"
        last_date_ch = ch_client.execute(query)[0][0]
        last_date_str = last_date_ch.strftime("%Y%m%d")
        print(f"🚀 开始审计 VOL-03/04 流动性数据，选取日期: {last_date_ch}")
    except Exception as e:
        print(f"❌ 无法从 ClickHouse 获取最新日期: {e}")
        return

    # A. 从 ClickHouse 获取全市场快照
    try:
        query = f"SELECT stock_code, turnover_rate, pe, pb, circ_mv FROM stock_valuation_local WHERE trade_date = '{last_date_ch}'"
        rows = ch_client.execute(query)
        df_ch = pd.DataFrame(rows, columns=['stock_code', 'turnover_rate', 'pe', 'pb', 'circ_mv'])
        df_ch = df_ch.set_index('stock_code').sort_index()
    except Exception as e:
        print(f"❌ 无法从 ClickHouse 获取数据: {e}")
        return

    # B. 从 Tushare 获取全市场快照
    try:
        df_ts = pro.daily_basic(trade_date=last_date_str)
        # 统一代码格式，Tushare 本身就是 000001.SZ 这种
        df_ts = df_ts[['ts_code', 'turnover_rate', 'pe', 'pb', 'circ_mv']].rename(columns={'ts_code': 'stock_code'})
        # 注意: Tushare circ_mv 单位是 万元，ClickHouse 可能也是万元 (需要核实)
        # 之前的 sync_mysql_to_ch 没做单位换算，假设一致
        df_ts = df_ts.set_index('stock_code').sort_index()
    except Exception as e:
        print(f"❌ 无法从 Tushare 获取数据: {e}")
        return

    # C. 合并对比
    comparison = df_ts.join(df_ch, lsuffix='_ts', rsuffix='_ch', how='outer')
    
    # 检查换手率差异 (允许 0.01 绝对差异)
    comparison['diff_turnover'] = (comparison['turnover_rate_ts'] - comparison['turnover_rate_ch']).abs().fillna(0)
    mismatch_turnover = comparison[comparison['diff_turnover'] > 0.01]
    
    # 检查 PE 差异 (允许 1% 相对差异)
    comparison['diff_pe_pct'] = ((comparison['pe_ts'] - comparison['pe_ch']).abs() / comparison['pe_ts']).fillna(0)
    mismatch_pe = comparison[(comparison['diff_pe_pct'] > 0.01) & (comparison['pe_ts'] > 0)]

    print(f"\n全市场数据核对结果 ({last_date_ch}):")
    print(f"   - Tushare 股票数: {len(df_ts)}")
    print(f"   - ClickHouse 股票数: {len(df_ch)}")
    
    missing_ch = comparison[comparison['turnover_rate_ch'].isna()]
    print(f"   - ClickHouse 缺失股票: {len(missing_ch)}")
    print(f"   - 换手率异常数 (>0.01): {len(mismatch_turnover)}")
    print(f"   - PE 异常数 (>1%): {len(mismatch_pe)}")
    
    if len(missing_ch) > 0:
        print(f"\n缺失样本 (前 5 条):")
        print(missing_ch.index[:5].tolist())

if __name__ == "__main__":
    audit_vol_03_04_liquidity()

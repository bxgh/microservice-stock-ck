"""
历史回填脚本: ads_l8_backtest_label
计算 L8 推送后的 T+N 收益率。
"""
import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
import logging

TZ_SH = ZoneInfo("Asia/Shanghai")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置信息
DB_CONFIG = {
    'host': 'sh-cdb-h7flpxu4.sql.tencentcdb.com',
    'port': 26300,
    'user': 'root',
    'password': 'alwaysup@888',
    'db': 'alwaysup',
    'charset': 'utf8mb4'
}

BENCHMARK_CODE = '000300.SH' # 沪深300

def get_conn():
    return pymysql.connect(**DB_CONFIG)

def load_trading_calendar():
    """获取所有交易日"""
    conn = get_conn()
    query = "SELECT cal_date FROM trade_cal WHERE is_open = 1 ORDER BY cal_date ASC"
    df = pd.read_sql(query, conn)
    conn.close()
    return df['cal_date'].tolist()

def get_tn_date(trading_days, base_date, n):
    """获取 T+N 的交易日"""
    try:
        # 确保 base_date 是 date 对象
        if isinstance(base_date, str):
            base_date = datetime.strptime(base_date, '%Y-%m-%d').date()
        
        idx = trading_days.index(base_date)
        if idx + n < len(trading_days):
            return trading_days[idx + n]
        return None
    except ValueError:
        # 如果 base_date 不在交易日列表中 (比如是非交易日推送，虽然不应该)
        # 寻找之后最近的一个交易日
        future_days = [d for d in trading_days if d > base_date]
        if future_days and n > 0:
            idx = trading_days.index(future_days[0])
            if idx + n - 1 < len(trading_days):
                return trading_days[idx + n - 1]
        return None

def backfill_labels(limit_days=30, incremental=False):
    """
    回填标注数据
    """
    trading_days = load_trading_calendar()
    conn = get_conn()
    
    if incremental:
        # 增量模式: 查找所有 ret_t30 为空且 trade_date 在 40 天内的记录
        query = """
            SELECT ts_code, trade_date, source_version, anomaly_category 
            FROM ads_l8_backtest_label 
            WHERE ret_t30 IS NULL 
            AND trade_date >= DATE_SUB(CURDATE(), INTERVAL 45 DAY)
            AND is_deleted = 0
        """
        signals_df = pd.read_sql(query, conn)
        logger.info(f"Incremental mode: Loaded {len(signals_df)} incomplete labels")
    else:
        # 全量/定期模式: 从主表读最近 N 天的推送记录
        query = """
            SELECT ts_code, trade_date, source_version, anomaly_category 
            FROM ads_l8_unified_signal 
            WHERE is_pushed = 1 
            AND trade_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            AND is_deleted = 0
        """
        signals_df = pd.read_sql(query, conn, params=(limit_days,))
        logger.info(f"Regular mode: Loaded {len(signals_df)} push signals from ads_l8_unified_signal")
    
    if signals_df.empty:
        return

    # 2. 批量获取 K 线数据 (加速计算)
    # 获取涉及的所有代码和日期范围
    unique_codes = signals_df['ts_code'].unique().tolist()
    unique_codes.append(BENCHMARK_CODE)
    
    # 最小和最大日期 (需要包含 T+30 范围)
    min_date = signals_df['trade_date'].min()
    max_date = datetime.now(TZ_SH).date()
    
    # 获取 K 线 (仅收盘价)
    kline_query = """
        SELECT ts_code, trade_date, close 
        FROM stock_kline_daily 
        WHERE ts_code IN %s AND trade_date >= %s
    """
    # 另外还需要从 ods_index_daily 获取基准价格
    index_query = """
        SELECT ts_code, trade_date, close 
        FROM ods_index_daily 
        WHERE ts_code = %s AND trade_date >= %s
    """
    
    # 获取股票价格
    logger.info("Fetching stock price data...")
    stock_prices = pd.read_sql(kline_query, conn, params=(unique_codes, min_date))
    
    # 获取基准价格
    logger.info("Fetching benchmark price data...")
    bench_prices = pd.read_sql(index_query, conn, params=(BENCHMARK_CODE, min_date))
    
    # 合并价格数据
    all_prices = pd.concat([stock_prices, bench_prices])
    # 构建快速查找索引 (ts_code, trade_date) -> close
    price_map = all_prices.set_index(['ts_code', 'trade_date'])['close'].to_dict()
    
    # 3. 计算收益率
    results = []
    for _, row in signals_df.iterrows():
        ts_code = row['ts_code']
        base_date = row['trade_date']
        
        base_price = price_map.get((ts_code, base_date))
        bench_base_price = price_map.get((BENCHMARK_CODE, base_date))
        
        if base_price is None or bench_base_price is None:
            continue
            
        label = {
            'ts_code': ts_code,
            'trade_date': base_date,
            'source_version': row['source_version'],
            'anomaly_category': row['anomaly_category']
        }
        
        # 计算各周期收益
        for n in [1, 5, 10, 20, 30]:
            target_date = get_tn_date(trading_days, base_date, n)
            if target_date:
                tn_price = price_map.get((ts_code, target_date))
                if tn_price:
                    ret = (float(tn_price) / float(base_price)) - 1
                    label[f'ret_t{n}'] = ret
                    
                # 针对 T+5 计算基准和 Alpha
                if n == 5:
                    bench_tn_price = price_map.get((BENCHMARK_CODE, target_date))
                    if bench_tn_price:
                        bench_ret = (float(bench_tn_price) / float(bench_base_price)) - 1
                        label['benchmark_ret_t5'] = bench_ret
                        if tn_price:
                            label['alpha_t5'] = ret - bench_ret
        
        results.append(label)
    
    logger.info(f"Calculated {len(results)} labels")
    
    # 4. 写入数据库 (批量)
    if not results:
        return
        
    df_results = pd.DataFrame(results)
    
    # 准备 INSERT IGNORE 或 REPLACE INTO 语句 (MySQL)
    # 使用 INSERT INTO ... ON DUPLICATE KEY UPDATE 保持 updated_at 更新
    cursor = conn.cursor()
    
    cols = list(df_results.columns)
    sql = "INSERT INTO ads_l8_backtest_label ({}) VALUES ({}) ON DUPLICATE KEY UPDATE {}".format(
        ", ".join(cols),
        ", ".join(["%s"] * len(cols)),
        ", ".join([f"{c}=VALUES({c})" for c in cols if c not in ['ts_code', 'trade_date', 'source_version']])
    )
    
    data = [tuple(row) for row in df_results.values]
    # 处理 NaN 为 None (MySQL NULL)
    data = [tuple(None if isinstance(v, float) and np.isnan(v) else v for v in r) for r in data]
    
    try:
        cursor.executemany(sql, data)
        conn.commit()
        logger.info(f"Successfully backfilled {cursor.rowcount} rows into MySQL")
    except Exception as e:
        logger.error(f"MySQL batch insert failed: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    # TODO: CK 双写逻辑可在此通过 API 触发同步或直接写入
    logger.info("Next step: Trigger Gate-3 audit to sync ClickHouse")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--incremental', action='store_true', help='Incremental mode')
    parser.add_argument('--days', type=int, default=30, help='Days for regular mode')
    args = parser.parse_args()
    
    backfill_labels(limit_days=args.days, incremental=args.incremental)

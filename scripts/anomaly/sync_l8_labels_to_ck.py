import pymysql
from clickhouse_driver import Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configs
MYSQL_CONFIG = {
    'host': 'sh-cdb-h7flpxu4.sql.tencentcdb.com',
    'port': 26300,
    'user': 'root',
    'password': 'alwaysup@888',
    'db': 'alwaysup'
}

CK_CONFIG = {
    'host': '127.0.0.1',
    'port': 9000,
    'user': 'default',
    'password': '',
    'database': 'stock_data'
}

def sync_labels():
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    cur.execute("SELECT * FROM ads_l8_backtest_label WHERE is_deleted = 0")
    rows = cur.fetchall()
    
    if not rows:
        logger.info("No rows to sync")
        return

    client = Client(**CK_CONFIG)
    
    # 准备数据
    data = []
    for r in rows:
        data.append((
            r['id'],
            r['ts_code'],
            r['trade_date'],
            r['source_version'],
            float(r['ret_t1']) if r['ret_t1'] is not None else 0.0,
            float(r['ret_t5']) if r['ret_t5'] is not None else 0.0,
            float(r['ret_t10']) if r['ret_t10'] is not None else 0.0,
            float(r['ret_t20']) if r['ret_t20'] is not None else 0.0,
            float(r['ret_t30']) if r['ret_t30'] is not None else 0.0,
            float(r['benchmark_ret_t5']) if r['benchmark_ret_t5'] is not None else 0.0,
            float(r['alpha_t5']) if r['alpha_t5'] is not None else 0.0,
            r['market_regime'] if r['market_regime'] is not None else '',
            r['anomaly_category'] if r['anomaly_category'] is not None else '',
            r['created_at'],
            r['updated_at'],
            r['is_deleted']
        ))
    
    sql = "INSERT INTO ads_l8_backtest_label VALUES"
    try:
        client.execute(sql, data)
        logger.info(f"Successfully synced {len(data)} rows to ClickHouse")
    except Exception as e:
        logger.error(f"Sync failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    sync_labels()

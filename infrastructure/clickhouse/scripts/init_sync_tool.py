import os
import pymysql
from clickhouse_driver import Client
from datetime import datetime, date, timedelta
import logging
from decimal import Decimal
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
MYSQL_CONFIG = {
    'host': os.getenv('GSD_DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('GSD_DB_PORT', 36301)),
    'user': os.getenv('GSD_DB_USER', 'root'),
    'password': os.getenv('GSD_DB_PASSWORD', 'alwaysup@888'),
    'database': os.getenv('GSD_DB_NAME', 'alwaysup'),
    'cursorclass': pymysql.cursors.DictCursor,
    'charset': 'utf8mb4'
}

CH_CONFIG = {
    'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
    'port': int(os.getenv('CLICKHOUSE_PORT', 9000)),
    'user': os.getenv('CLICKHOUSE_USER', 'admin'),
    'password': os.getenv('CLICKHOUSE_PASSWORD', 'admin123'),
    'database': os.getenv('CLICKHOUSE_DB', 'stock_data')
}

TABLES_TO_SYNC = [
    ('daily_basic', 'daily_basic', 'trade_date'),
    ('stock_kline_daily', 'stock_kline_daily', 'trade_date'),
    ('ods_index_daily', 'ods_index_daily', 'trade_date'),
    ('stock_finance_indicators', 'stock_finance_indicators', 'report_date'),
    ('stock_balance_sheet', 'stock_balance_sheet', 'report_date'),
    ('stock_income_statement', 'stock_income_statement', 'report_date'),
    ('stock_cash_flow_statement', 'stock_cash_flow_statement', 'report_date'),
    ('stock_basic_info', 'stock_basic_info', None),
    ('ods_sw_index_daily', 'ods_sw_index_daily', 'trade_date'),
    ('ads_l1_market_overview', 'ads_l1_market_overview', 'trade_date'),
    ('ads_l2_industry_daily', 'ads_l2_industry_daily', 'trade_date'),
]

def sync_table_optimized(mysql_conn, ch_client, mysql_table, ch_table, date_col):
    logger.info(f"Starting optimized sync for table {mysql_table} -> {ch_table}")
    
    cursor = mysql_conn.cursor()
    
    # Fetch columns from ClickHouse
    ch_columns_info = ch_client.execute(f"DESCRIBE TABLE {ch_table}")
    ch_columns = [col[0] for col in ch_columns_info if col[0] != 'updated_at']
    
    if not date_col:
        # Fallback to simple offset if no date column
        logger.info(f"No date column for {mysql_table}, using offset pagination")
        cursor.execute(f"SELECT COUNT(*) as count FROM {mysql_table}")
        total_count = cursor.fetchone()['count']
        batch_size = 50000
        offset = 0
        while offset < total_count:
            cursor.execute(f"SELECT {', '.join(ch_columns)} FROM {mysql_table} LIMIT {batch_size} OFFSET {offset}")
            rows = cursor.fetchall()
            if not rows: break
            insert_into_ch(ch_client, ch_table, ch_columns, rows)
            offset += len(rows)
            logger.info(f"Synced {offset}/{total_count} rows for {ch_table}")
        return

    # Get date range
    cursor.execute(f"SELECT MIN({date_col}) as min_d, MAX({date_col}) as max_d FROM {mysql_table}")
    res = cursor.fetchone()
    min_date = res['min_d']
    max_date = res['max_d']
    
    if not min_date or not max_date:
        logger.info(f"Table {mysql_table} has no date data. Skipping.")
        return

    logger.info(f"Date range for {mysql_table}: {min_date} to {max_date}")

    current_start = min_date
    delta = timedelta(days=30) # Process 1 month at a time
    
    total_synced = 0
    while current_start <= max_date:
        current_end = current_start + delta
        logger.info(f"Syncing {mysql_table} range: {current_start} to {current_end}")
        
        # We don't use ORDER BY here to speed up MySQL query, as date range is already small
        # and ClickHouse will handle the sorting during merge.
        query = f"SELECT {', '.join(ch_columns)} FROM {mysql_table} WHERE {date_col} >= %s AND {date_col} < %s"
        cursor.execute(query, (current_start, current_end))
        rows = cursor.fetchall()
        
        if rows:
            insert_into_ch(ch_client, ch_table, ch_columns, rows)
            total_synced += len(rows)
            logger.info(f"Synced {len(rows)} rows for {ch_table} (Total: {total_synced})")
            
        current_start = current_end

def insert_into_ch(ch_client, ch_table, ch_columns, rows):
    data = []
    for row in rows:
        processed_row = []
        for col in ch_columns:
            val = row.get(col)
            if isinstance(val, Decimal):
                val = float(val)
            processed_row.append(val)
        data.append(tuple(processed_row))
    
    query = f"INSERT INTO {ch_table} ({', '.join(ch_columns)}) VALUES"
    ch_client.execute(query, data)

def main():
    start_time = time.time()
    try:
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        ch_client = Client(**CH_CONFIG)
        
        for mysql_table, ch_table, date_col in TABLES_TO_SYNC:
            try:
                sync_table_optimized(mysql_conn, ch_client, mysql_table, ch_table, date_col)
            except Exception as e:
                logger.error(f"Error syncing {mysql_table}: {e}")
                
    except Exception as e:
        logger.error(f"Main sync error: {e}")
    finally:
        if 'mysql_conn' in locals() and mysql_conn:
            mysql_conn.close()
    
    duration = time.time() - start_time
    logger.info(f"Total sync duration: {duration:.2f} seconds")

if __name__ == "__main__":
    main()

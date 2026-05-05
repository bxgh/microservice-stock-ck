#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Basic Data Backfill Script (Tushare 增强版)
自动安装依赖，扫描 MySQL 缺失日期，批量获取并入库。
"""
import os
import sys
import subprocess
import time
from datetime import datetime, timedelta

def install_deps():
    print("Checking dependencies...")
    try:
        import pymysql
        import sqlalchemy
        print("Dependencies validated.")
    except ImportError:
        print("Missing dependencies. Installing PyMySQL and SQLAlchemy...")
        env = os.environ.copy()
        env['http_proxy'] = "http://192.168.151.18:3128"
        env['https_proxy'] = "http://192.168.151.18:3128"
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMySQL", "SQLAlchemy"], env=env)
        print("Installation complete.")

install_deps()

import tushare as ts
import pandas as pd
from sqlalchemy import create_engine, text

# Configuration
os.environ.setdefault("TZ", "Asia/Shanghai")
os.environ["http_proxy"] = "http://192.168.151.18:3128"
os.environ["https_proxy"] = "http://192.168.151.18:3128"
time.tzset()

# MySQL details (Fallback to hardcoded if not in env)
db_host = os.getenv("GSD_DB_HOST", "127.0.0.1")
db_port = os.getenv("GSD_DB_PORT", "36301")
db_user = os.getenv("GSD_DB_USER", "root")
db_password = os.getenv("GSD_DB_PASSWORD", "alwaysup@888")
db_name = os.getenv("GSD_DB_NAME", "alwaysup")

import urllib.parse
encoded_password = urllib.parse.quote_plus(db_password)
engine_url = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
engine = create_engine(engine_url)

# Setup Tushare
token = os.getenv("TUSHARE_TOKEN", "")
if not token:
    # Try reading from config file
    try:
        with open("/app/.env.tushare", "r") as f:
            for line in f:
                if line.startswith("TUSHARE_TOKEN="):
                    token = line.strip().split("=")[1]
    except Exception as e:
        pass

if not token:
    print("FATAL ERROR: TUSHARE_TOKEN not found.")
    sys.exit(1)

ts.set_token(token)
pro = ts.pro_api()

def get_db_dates():
    """获取数据库中已有的且大于某日的 trade_date 集合"""
    query = "SELECT DISTINCT trade_date FROM daily_basic WHERE trade_date >= '2025-08-01' ORDER BY trade_date"
    with engine.connect() as conn:
        res = conn.execute(text(query)).fetchall()
        # Convert date to YYYYMMDD
        return {r[0].strftime("%Y%m%d") for r in res}

def get_trade_cal(start_date, end_date):
    """获取A股交易日历"""
    df = pro.trade_cal(exchange='SSE', is_open='1', start_date=start_date, end_date=end_date)
    return df['cal_date'].tolist()

def write_to_db(df):
    """通过临时表实现 Insert Ignore / On Duplicate Update 逻辑 (或先删后插)"""
    trade_date = df['trade_date'].iloc[0]
    date_str_formatted = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
    
    with engine.begin() as conn:
        # Delete existing data for this date to prevent primary key collisions
        conn.execute(text(f"DELETE FROM daily_basic WHERE trade_date = '{date_str_formatted}'"))
        
        # Convert YYYYMMDD to YYYY-MM-DD for standard format in MySQL
        df['trade_date'] = date_str_formatted
        
        # Bulk Insert
        df.to_sql('daily_basic', con=conn, if_exists='append', index=False, chunksize=2000)
        print(f"[{date_str_formatted}] 成功插入 {len(df)} 条记录.")

def backfill():
    print(f"Connecting to MySQL: {db_host}:{db_port}/{db_name}")
    start_date = "20250808"
    end_date = datetime.now().strftime("%Y%m%d")
    
    cal_dates = get_trade_cal(start_date, end_date)
    existing_dates = get_db_dates()
    
    missing_dates = sorted(list(set(cal_dates) - set(existing_dates)))
    if not missing_dates:
        print("No missing dates in the specified range. DB is up to date!")
        return
        
    print(f"Found {len(missing_dates)} missing dates. Starting backfill...")
    
    for i, date in enumerate(missing_dates):
        print(f"Fetching data for {date} ({i+1}/{len(missing_dates)})...")
        try:
            df = pro.daily_basic(trade_date=date)
            if df.empty:
                print(f"[{date}] 返回数据为空, 可能尚未开盘或已停牌休市跳过。")
                continue
                
            # Filter BJ stocks
            df = df[~df['ts_code'].str.endswith('.BJ')]
            
            write_to_db(df)
            
            # API rate limit safety (daily_basic has 200/min limit usually)
            time.sleep(0.5)
            
        except Exception as e:
            print(f"!!! Error fetching data for {date}: {e}")
            break

if __name__ == "__main__":
    backfill()

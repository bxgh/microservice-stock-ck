#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Basic Data Sync Script
仅同步当前交易日或最近一次交易日的数据。
适用于每日定时调度。
"""
import os
import sys
import subprocess
import time
from datetime import datetime
import urllib.parse

def install_deps():
    try:
        import pymysql
        import sqlalchemy
    except ImportError:
        env = os.environ.copy()
        env['http_proxy'] = "http://192.168.151.18:3128"
        env['https_proxy'] = "http://192.168.151.18:3128"
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMySQL", "SQLAlchemy"], env=env)

install_deps()

import tushare as ts
import pandas as pd
from sqlalchemy import create_engine, text

os.environ.setdefault("TZ", "Asia/Shanghai")
os.environ["http_proxy"] = "http://192.168.151.18:3128"
os.environ["https_proxy"] = "http://192.168.151.18:3128"
time.tzset()

db_host = os.getenv("GSD_DB_HOST", "127.0.0.1")
db_port = os.getenv("GSD_DB_PORT", "36301")
db_user = os.getenv("GSD_DB_USER", "root")
db_password = os.getenv("GSD_DB_PASSWORD", "alwaysup@888")
db_name = os.getenv("GSD_DB_NAME", "alwaysup")

encoded_password = urllib.parse.quote_plus(db_password)
engine_url = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
engine = create_engine(engine_url)

token = os.getenv("TUSHARE_TOKEN", "")
if not token:
    try:
        with open("/app/.env.tushare", "r") as f:
            for line in f:
                if line.startswith("TUSHARE_TOKEN="):
                    token = line.strip().split("=")[1]
    except Exception:
        pass

if not token:
    print("FATAL ERROR: TUSHARE_TOKEN not found.")
    sys.exit(1)

ts.set_token(token)
pro = ts.pro_api()

def get_last_trade_date():
    today = datetime.now().strftime("%Y%m%d")
    df_cal = pro.trade_cal(exchange='SSE', is_open='1', end_date=today)
    if not df_cal.empty:
        return df_cal.iloc[-1]['cal_date']
    return today

def sync():
    last_trade_date = get_last_trade_date()
    print(f"[{datetime.now()}] Triggering sync for trade_date: {last_trade_date}")
    
    try:
        df = pro.daily_basic(trade_date=last_trade_date)
        if df.empty:
            print(f"Data for {last_trade_date} is empty. Market might be closed or data not ready.")
            return

        # 剔除北交所
        df = df[~df['ts_code'].str.endswith('.BJ')]
        
        date_str_formatted = f"{last_trade_date[:4]}-{last_trade_date[4:6]}-{last_trade_date[6:]}"
        
        with engine.begin() as conn:
            conn.execute(text(f"DELETE FROM daily_basic WHERE trade_date = '{date_str_formatted}'"))
            df['trade_date'] = date_str_formatted
            df.to_sql('daily_basic', con=conn, if_exists='append', index=False, chunksize=2000)
            print(f"Successfully synced {len(df)} records for {date_str_formatted}.")
            
    except Exception as e:
        print(f"Error during sync: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync()

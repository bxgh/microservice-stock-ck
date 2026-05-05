#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
原油期货历史K线数据回填脚本 (EPIC-019)
用于将 WTI(CL) 和 Brent(OIL) 的历史日线数据通过 mootdx-source 同步到 ClickHouse。
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
import pandas as pd
from clickhouse_driver import Client

# 添加被 grpc 编译出的存放位置作为 Python 查找路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../gsd-worker/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

import grpc
from datetime import datetime, timedelta
import io
from datasource.v1 import data_source_pb2
from datasource.v1 import data_source_pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SyncFuturesData")

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_TCP_PORT", 9000))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "admin")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "admin123")

MOOTDX_GRPC_ADDRESS = os.getenv("MOOTDX_GRPC_ADDRESS", "localhost:50051")

async def fetch_futures_data(symbol: str) -> pd.DataFrame:
    """通过 gRPC 调用 mootdx-source 获取原油数据"""
    logger.info(f"Connecting to mootdx-source at {MOOTDX_GRPC_ADDRESS}")
    async with grpc.aio.insecure_channel(MOOTDX_GRPC_ADDRESS) as channel:
        stub = data_source_pb2_grpc.DataSourceServiceStub(channel)
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_FUTURES_KLINE_DAILY,
            codes=[symbol],
            params={},
            request_id=f"sync_futures_{symbol}_{int(datetime.now().timestamp())}"
        )
        
        try:
            response = await stub.FetchData(request)
            if not response.success:
                logger.error(f"Failed to fetch data for {symbol}: {response.error_message}")
                return pd.DataFrame()
                
            if response.format == "JSON":
                from io import StringIO
                df = pd.read_json(StringIO(response.json_data), orient="records")
                if "trade_date" in df.columns:
                    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
                return df
            else:
                logger.error(f"Unsupported format: {response.format}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"gRPC call failed: {e}")
            return pd.DataFrame()

def save_to_clickhouse(df: pd.DataFrame, symbol: str):
    """保存到 ClickHouse"""
    if df.empty:
        logger.warning(f"No data to save for {symbol}")
        return
        
    client = Client(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT, user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD)
    
    # 按照 futures_kline_daily 结构转换列名
    # akshare: 日期, 开盘, 最高, 最低, 收盘, 成交量, 等等(可能中英文会有差异，脚本中做动态适配)
    col_mapping = {
        'open': 'open_price',
        '开盘': 'open_price',
        'high': 'high_price',
        '最高': 'high_price',
        'low': 'low_price',
        '最低': 'low_price',
        'close': 'close_price',
        '收盘': 'close_price',
        'volume': 'volume',
        '成交量': 'volume'
    }
    
    # 重命名列
    df = df.rename(columns=col_mapping)
    
    # 丢弃如果因为服务层和本层双重赋值造成的重复列
    df = df.loc[:,~df.columns.duplicated()].copy()
    
    required_cols = ['symbol', 'trade_date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
    
    # 填充可能缺少的数值
    for col in ['open_price', 'high_price', 'low_price', 'close_price']:
        if col not in df.columns:
            logger.error(f"Missing price column {col} for {symbol}, original columns: {df.columns.tolist()}")
            return
            
    if 'volume' not in df.columns:
        df['volume'] = 0
    if 'symbol' not in df.columns:
        df['symbol'] = symbol
        
    # 筛选最后1年 (2025-01-01 及之后)
    cutoff_date = pd.to_datetime('2025-01-01')
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df[df['trade_date'] >= cutoff_date]
    df['trade_date'] = df['trade_date'].dt.date
    
    # 选出需要的列并保持顺序类型一致
    df = df[required_cols].copy()
    df['open_price'] = df['open_price'].astype(float)
    df['high_price'] = df['high_price'].astype(float)
    df['low_price'] = df['low_price'].astype(float)
    df['close_price'] = df['close_price'].astype(float)
    df['volume'] = df['volume'].fillna(0).astype('uint64')
    
    records = df.to_dict('records')
    logger.info(f"Inserting {len(records)} records for {symbol} to ClickHouse...")
    
    query = """
        INSERT INTO stock_data.futures_kline_daily 
        (symbol, trade_date, open_price, high_price, low_price, close_price, volume) 
        VALUES
    """
    
    try:
        client.execute(query, records)
        logger.info(f"Successfully inserted data for {symbol}.")
    except Exception as e:
        logger.error(f"Failed to insert data to ClickHouse for {symbol}: {e}")

async def main():
    symbols = ["CL", "OIL"]
    for symbol in symbols:
        logger.info(f"=== Process {symbol} ===")
        df = await fetch_futures_data(symbol)
        if not df.empty:
            logger.info(f"Fetched {len(df)} rows for {symbol}. First date: {df.iloc[0].get('date', df.iloc[0].get('日期', ''))}, Last date: {df.iloc[-1].get('date', df.iloc[-1].get('日期', ''))}")
            save_to_clickhouse(df, symbol)
        else:
            logger.warning(f"No data fetched for {symbol}.")

if __name__ == "__main__":
    asyncio.run(main())

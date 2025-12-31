"""
Unified Data Source Collector
Uses gRPC client to fetch data from mootdx-source.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.grpc_client.client import get_datasource_client, DataSourceClient
from src.config.settings import settings

logger = logging.getLogger(__name__)

class DataSourceCollector:
    """Collector that uses the unified mootdx-source gRPC service"""
    
    def __init__(self):
        self.client: Optional[DataSourceClient] = None
        self._semaphore = asyncio.Semaphore(settings.max_workers)

    async def initialize(self):
        """Initialize the gRPC client"""
        if not self.client:
            self.client = await get_datasource_client()
            logger.info("✅ DataSourceCollector initialized (gRPC)")

    async def get_stock_list(self) -> List[str]:
        """获取全市场 A 股列表"""
        await self.initialize()
        try:
            # fetch_meta("all") returns all stocks metadata
            df = await self.client.fetch_meta("all")
            if df.empty:
                logger.warning("Empty stock list returned from DataSource")
                return []
            
            # Extract codes and ensure proper format (with sh./sz. prefix if needed)
            # mootdx-source usually returns shxxxxxx or szxxxxxx
            # If it's just 6 digits, we might need to add prefix
            # check the first row to determine format
            codes = []
            for _, row in df.iterrows():
                code = str(row['code'])
                # If code is like '600000', add prefix based on exchange
                # Baostock format: 'sh.600000'
                if '.' not in code and len(code) == 6:
                    if code.startswith(('60', '68')):
                        code = f"sh.{code}"
                    elif code.startswith(('00', '30', '002')):
                        code = f"sz.{code}"
                codes.append(code)
                
            # Filter for individual stocks (sh.60, sz.00, sz.30, sh.68)
            valid_stocks = [c for c in codes if c.startswith(('sh.60', 'sz.00', 'sz.30', 'sh.68'))]
            logger.info(f"获取到全市场股票数量: {len(valid_stocks)}")
            return valid_stocks
        except Exception as e:
            logger.error(f"Error getting stock list: {e}")
            return []

    async def close(self):
        """Close the data source collector"""
        # gRPC client is a singleton, managed globally
        # No need to close the client here
        logger.info("DataSourceCollector closed")

    def _validate_data_integrity(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        内部方法：校验数据完整性与逻辑正确性 (向量化处理)
        
        校验项：
        1. 价格不能为负数 (OHLC)
        2. 成交量与成交额不能为负数
        3. 价格逻辑关系：High >= Low, High >= Open/Close, Low <= Open/Close
        """
        if df.empty:
            return df

        initial_count = len(df)
        
        # 1. 价格非负校验
        price_cols = ['open', 'high', 'low', 'close']
        valid_mask = (df[price_cols] >= 0).all(axis=1)
        
        # 2. 成交量/额非负校验
        vol_cols = ['volume', 'amount']
        if all(col in df.columns for col in vol_cols):
            valid_mask &= (df[vol_cols] >= 0).all(axis=1)
            
        # 3. 价格逻辑关系校验
        # High 必须是最高，Low 必须是最低
        logic_mask = (df['high'] >= df['low']) & \
                     (df['high'] >= df['open']) & \
                     (df['high'] >= df['close']) & \
                     (df['low'] <= df['open']) & \
                     (df['low'] <= df['close'])
        
        valid_mask &= logic_mask
        
        # 过滤无效数据
        df_cleaned = df[valid_mask].copy()
        
        removed_count = initial_count - len(df_cleaned)
        if removed_count > 0:
            logger.warning(f"⚠️ {stock_code} 发现逻辑异常数据，已剔除 {removed_count}/{initial_count} 条记录")
            
        return df_cleaned



    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def collect_daily_kline(
        self, 
        stock_code: str, 
        start_date: str, 
        end_date: str,
        adjustflag: str = "3"  # 1:后复权, 2:前复权, 3:不复权
    ) -> List[Dict]:
        """采集单只股票日K线数据"""
        await self.initialize()
        
        # adjust mapping for fetch_history
        # mootdx-source (baostock): 1=backward, 2=forward, 3=none
        # data-collector input: 1:后复权, 2:前复权, 3:不复权
        adj_map = {
            "1": "1", # backward
            "2": "2", # forward
            "3": "3"  # none
        }
        grpc_adjust = adj_map.get(adjustflag, "3")

        try:
            async with self._semaphore:
                # fetch_history(code, start_date, end_date, frequency, adjust)
                # code format in mootdx-source might be different, 
                # but it usually handles sh.xxxxxx or just xxxxxx
                # let's pass as is first
                df = await self.client.fetch_history(
                    code=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjust=grpc_adjust
                )
            
            # P2.1: 数据完整性校验
            if df.empty or len(df) == 0:
                logger.warning(f"Empty data returned for {stock_code}")
                return []
            
            # 校验关键字段是否有 NaN
            critical_cols = ['open', 'close', 'high', 'low']
            if any(col in df.columns for col in critical_cols):
                if df[critical_cols].isnull().any().any():
                    logger.error(f"Invalid OHLC data (NaN detected) for {stock_code}")
                    return []
            
            # P2.2: 深度逻辑校验 (非负、OHLC 关系)
            df = self._validate_data_integrity(df, stock_code)
            if df.empty:
                logger.warning(f"No valid data left after integrity check for {stock_code}")
                return []
            
            # Ensure columns match what ClickHouseWriter/MySQLCloudWriter expect
            # Expected columns: date, code, open, high, low, close, volume, amount, turn, pctChg, peTTM, psTTM, pbMRQ, adj_factor
            # Baostock output had these. Mootdx-source output might vary.
            # We need to normalize it.
            
            # Normalize column names if needed
            rename_map = {
                'datetime': 'trade_date',
                'date': 'trade_date',
                'vol': 'volume',
                'turnover': 'turnover_rate',
                'turn': 'turnover_rate',
                'code': 'stock_code'
            }
            df = df.rename(columns=rename_map)
            
            # Ensure stock_code exists
            if 'stock_code' not in df.columns:
                 df['stock_code'] = stock_code
            
            # Ensure all required columns exist (default to 0 if missing)
            required_cols = ['trade_date', 'stock_code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover_rate', 'adj_factor']
            for col in required_cols:
                if col not in df.columns:
                    if col in ['trade_date', 'stock_code']:
                        continue # Should not happen
                    df[col] = 0.0
            
            return df[required_cols].to_dict(orient='records')
            
        except Exception as e:
            logger.error(f"Error collecting K-line for {stock_code}: {e}")
            return []

    async def collect_financials(self, stock_code: str) -> List[Dict]:
        """采集单只股票财务数据 (预留给 Story 10.3)"""
        await self.initialize()
        try:
            df = await self.client.fetch_finance(stock_code)
            if df.empty:
                return []
            return df.to_dict(orient='records')
        except Exception as e:
            logger.error(f"Error collecting financials for {stock_code}: {e}")
            return []

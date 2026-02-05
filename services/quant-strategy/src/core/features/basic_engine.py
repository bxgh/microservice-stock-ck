
"""
基础特征向量构建引擎 (VectorEngine)
对应 Story 002.02: BasicFeatureEngine
负责生成向量 A (主动强度), B (盘口失衡), C (收益率)
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from adapters.clickhouse_loader import ClickHouseLoader

logger = logging.getLogger(__name__)

class BasicFeatureEngine:
    def __init__(self, loader: ClickHouseLoader = None):
        self.loader = loader if loader else ClickHouseLoader()
        
    def calculate_vector_a(self, ticks_df: pd.DataFrame, trade_date_str: str) -> pd.Series:
        """
        计算向量 A: 主动买入强度 (Lee-Ready)
        """
        if ticks_df.empty:
            return pd.Series(dtype=float)
            
        df = ticks_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['tick_time']):
             df['datetime'] = pd.to_datetime(trade_date_str + ' ' + df['tick_time'])
        else:
            df['datetime'] = df['tick_time']

        df = df.set_index('datetime')
        
        # Direction: 0=Neutral, 1=Buy, 2=Sell (Common in A-share ticks like Mootdx/Tongdaixin)
        # Verify: standard usually 1=Buy(red), 2=Sell(green).
        
        # Group by 1min
        # Resample logic aligned with 240 mins (09:31-11:30, 13:01-15:00)
        # We use the same grid logic as cleaner, but simplified here for calculation first
        
        # Calculate Net Active Vol
        # Buy Vol
        df['buy_vol'] = np.where(df['direction'] == 1, df['volume'], 0)
        df['sell_vol'] = np.where(df['direction'] == 2, df['volume'], 0)
        
        resampled = df.resample('1min', label='right', closed='right').agg({
            'buy_vol': 'sum',
            'sell_vol': 'sum',
            'volume': 'sum'
        })
        
        # Avoid division by zero
        # Vector A = (Buy - Sell) / Total
        vec_a = (resampled['buy_vol'] - resampled['sell_vol']) / resampled['volume'].replace(0, np.nan)
        return vec_a.fillna(0.0) # 0 vol means 0 intensity

    def calculate_vector_b(self, snapshots_df: pd.DataFrame) -> pd.Series:
        """
        计算向量 B: 盘口失衡度 (OBI)
        Formula: Sum(w_i * (Bi - Si) / (Bi + Si)) / Sum(w_i) ?
        Or plain weighted sum: w_1 * Imb1 + w_2 * Imb2 ...
        Design Doc: "wi * (Bi - Si) / (Bi + Si)" implies summing these up.
        Weights: [1.0, 0.8, 0.6, 0.4, 0.2]
        """
        if snapshots_df.empty:
            return pd.Series(dtype=float)
            
        df = snapshots_df.copy()
        # Time index
        if not pd.api.types.is_datetime64_any_dtype(df['snapshot_time']):
            df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])
        df = df.set_index('snapshot_time')
        
        weights = [1.0, 0.8, 0.6, 0.4, 0.2]
        obi_sum = 0.0
        
        for i in range(1, 6):
            bid_v = df[f'bid_volume{i}']
            ask_v = df[f'ask_volume{i}']
            total = bid_v + ask_v
            
            # Imbalance at level i
            imb = (bid_v - ask_v) / total.replace(0, np.nan)
            imb = imb.fillna(0.0) # If both 0, imbalance is 0
            
            obi_sum += weights[i-1] * imb
            
        # Normalize? Not derived in formula, but sums of weights = 3.0.
        # It's fine to return raw weighted sum as "Score".
        df['obi'] = obi_sum
        
        # Resample to 1min (Mean OBI)
        resampled_obi = df['obi'].resample('1min', label='right', closed='right').mean()
        return resampled_obi.fillna(0.0)

    def calculate_vector_c(self, snapshots_df: pd.DataFrame) -> pd.Series:
        """
        计算向量 C: 分时累积收益率
        Formula: Log(Price_t / Open_0930)
        Uses minute close prices.
        """
        if snapshots_df.empty:
            return pd.Series(dtype=float)

        df = snapshots_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['snapshot_time']):
            df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])
        df = df.set_index('snapshot_time')
        
        if df.empty:
            return pd.Series(dtype=float)

        # Ensure float type for price with coerce
        df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce').fillna(0).astype(float)
        
        minute_df = df['current_price'].resample('1min', label='right', closed='right').last()
        minute_df = minute_df.ffill() # Fill gaps
        
        # Determine Open Price (09:30 or first available)
        # Ideally the Open price of the day.
        # If we have the full df, we can find the open price.
        # Use the first valid price of the day?
        # Or specifically 09:30? The doc says "Price_open_0930".
        # Let's try to get the VERY first price in the dataframe (assuming it starts at 9:30)
        if minute_df.empty:
            return pd.Series(dtype=float)
            
        # Safe open price extraction
        first_valid_price = df['current_price'].iloc[0]
        if pd.isna(first_valid_price) or first_valid_price == 0:
             # Try to find first non-zero
             valid_prices = df[df['current_price'] > 0]['current_price']
             if valid_prices.empty:
                 return pd.Series(dtype=float)
             open_price = float(valid_prices.iloc[0])
        else:
             open_price = float(first_valid_price)
        if open_price == 0:
             # Fallback to minute open? Or 1.0 to avoid log(0) error
             open_price = 1.0
             
        # Log Return
        vec_c = np.log(minute_df / open_price)
        return vec_c.fillna(0.0)

    def align_vectors(self, vec_a: pd.Series, vec_b: pd.Series, vec_c: pd.Series, date_str: str) -> pd.DataFrame:
        """
        对齐三个向量到标准的 240 分钟网格
        """
        # Create standard grid
        morning_range = pd.date_range(start=f"{date_str} 09:31:00", 
                                      end=f"{date_str} 11:30:00", 
                                      freq='1min')
        afternoon_range = pd.date_range(start=f"{date_str} 13:01:00", 
                                        end=f"{date_str} 15:00:00", 
                                        freq='1min')
        full_grid = morning_range.union(afternoon_range)
        
        df = pd.DataFrame(index=full_grid)
        df['vector_a'] = vec_a
        df['vector_b'] = vec_b
        df['vector_c'] = vec_c
        
        # Fill Hints:
        # A (Active): Fill with 0 (No activity)
        # B (OBI): Fill with ffill? Or 0? OBI usually persists. ffill is safer.
        # C (Return): Fill with ffill (Price stays constant).
        
        df['vector_a'] = df['vector_a'].fillna(0.0)
        df['vector_b'] = df['vector_b'].ffill().fillna(0.0)
        df['vector_c'] = df['vector_c'].ffill().fillna(0.0)
        
        return df

    def process_stock(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """
        主入口：计算指定股票单日的所有特征
        """
        # 1. Load Data
        ticks = self.loader.get_ticks(stock_code, trade_date)
        snapshots = self.loader.get_snapshots(stock_code, trade_date)
        
        # 2. Calc Vectors
        vec_a = self.calculate_vector_a(ticks, trade_date)
        vec_b = self.calculate_vector_b(snapshots)
        vec_c = self.calculate_vector_c(snapshots)
        
        # 3. Align
        result = self.align_vectors(vec_a, vec_b, vec_c, trade_date)
        return result

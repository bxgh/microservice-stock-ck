
"""
流动性风控与预警 (LiquidityGatekeeper)
对应 Story 002.04
负责计算 VPIN (毒性) 和 Kyle's Lambda (冲击成本)
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from adapters.clickhouse_loader import ClickHouseLoader

logger = logging.getLogger(__name__)

class LiquidityGatekeeper:
    def __init__(self, loader: ClickHouseLoader = None):
        self.loader = loader if loader else ClickHouseLoader()

    def _estimate_buy_sell_volume(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        使用 Bulk Volume Classification (BVC) 估算买卖量
        V_buy = V_bucket * (Close - Low) / (High - Low)
        V_sell = V_bucket - V_buy
        
        Args:
            df: DataFrame containing 'close', 'high', 'low', 'volume'
        """
        # Handle High=Low case
        range_hl = df['high'] - df['low']
        ratio = (df['close'] - df['low']) / range_hl.replace(0, np.nan)
        
        # If High=Low:
        # If Close > PrevClose? Not available in bucket context easily without history.
        # Fallback: 0.5 (Neutral) or rely on tick direction if available?
        # BVC is for aggregated bars. 
        # Here we apply BVC on the "Bucket" bar.
        ratio = ratio.fillna(0.5) 
        
        buy_vol = df['volume'] * ratio
        sell_vol = df['volume'] * (1 - ratio)
        
        return buy_vol, sell_vol

    def calculate_vpin(self, ticks_df: pd.DataFrame, avg_daily_vol: float = 10000000) -> pd.DataFrame:
        """
        计算 VPIN (Volume-Synchronized Probability of Informed Trading)
        
        1. Determine Bucket Size
        2. Group into Buckets
        3. Rolling VPIN
        """
        if ticks_df.empty:
            return pd.DataFrame()
            
        df = ticks_df.copy()
        
        # 1. Determine Bucket Size
        # Ensure Types
        df['volume'] = df['volume'].astype(float) # Usually int but safe to cast
        df['price'] = df['price'].astype(float)
        
        # Rules:
        # < 10M: 200k
        # 10M - 50M: 500k
        # > 50M: 1M
        if avg_daily_vol < 10000000:
            bucket_vol_size = 200000
        elif avg_daily_vol < 50000000:
            bucket_vol_size = 500000
        else:
            bucket_vol_size = 1000000
            
        # 2. Assign Buckets
        # We need cumulative volume to slice buckets.
        df['cum_vol'] = df['volume'].cumsum()
        
        # Bucket ID = Floor(CumVol / Size)
        df['bucket_id'] = (df['cum_vol'] // bucket_vol_size).astype(int)
        
        # Group by Bucket ID to get OHLCV per bucket
        # Note: Ticks price is `price`. 
        # For BVC, we need Open/High/Low/Close of the BUCKET.
        
        bucket_aggs = df.groupby('bucket_id').agg({
            'price': ['first', 'max', 'min', 'last'],
            'volume': 'sum',
            'tick_time': 'last' # Timestamp of bucket completion
        })
        bucket_aggs.columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        
        # 3. Calculate Buy/Sell Vol using BVC
        buy_vol, sell_vol = self._estimate_buy_sell_volume(bucket_aggs)
        bucket_aggs['buy_vol'] = buy_vol
        bucket_aggs['sell_vol'] = sell_vol
        
        # 4. Calculate OI (Order Imbalance) = |Buy - Sell|
        bucket_aggs['oi'] = (bucket_aggs['buy_vol'] - bucket_aggs['sell_vol']).abs()
        
        # 5. Rolling VPIN (Window = 50 buckets)
        window = 50
        # VPIN = Sum(OI, 50) / Sum(Vol, 50)
        # Using rolling sum
        rolling_oi = bucket_aggs['oi'].rolling(window=window).sum()
        rolling_vol = bucket_aggs['volume'].rolling(window=window).sum()
        
        bucket_aggs['VPIN'] = rolling_oi / rolling_vol.replace(0, np.nan)
        
        # 6. Standardization (Z-Score) - Optional, need history. 
        # Skipping Z-Score for single-day calculation as per doc "Standardization (Optional)".
        
        # Return Bucket Time and VPIN
        return bucket_aggs[['timestamp', 'VPIN']].dropna()

    def calculate_lambda(self, ticks_df: pd.DataFrame, trade_date_str: str) -> pd.DataFrame:
        """
        计算 Kyle's Lambda (价格冲击系数)
        Regression: Return(bps) ~ NetAmt
        Window: 30 min
        """
        if ticks_df.empty:
            return pd.DataFrame()
            
        df = ticks_df.copy()
        
        # Time Index
        if not pd.api.types.is_datetime64_any_dtype(df['tick_time']):
             df['datetime'] = pd.to_datetime(trade_date_str + ' ' + df['tick_time'])
        else:
            df['datetime'] = df['tick_time']
        df = df.set_index('datetime')
        
        # Resample to 1 minute
        # We need:
        # P_t (Close Price)
        # SignedVolume (BuyAmt - SellAmt)
        
        df['signed_amount'] = np.where(df['direction'] == 1, df['amount'], 
                                       np.where(df['direction'] == 2, -df['amount'], 0)).astype(float)
        
        # Ensure price is float
        df['price'] = df['price'].astype(float)

        resampled = df.resample('1min', label='right', closed='right').agg({
            'price': 'last', # Close Price P_t
            'signed_amount': 'sum' # SignedVolume
        }).dropna()
        
        # Calculate Returns (bps)
        # Ret_t = (P_t - P_{t-1}) / P_{t-1}
        resampled['prev_price'] = resampled['price'].shift(1)
        resampled['ret_bps'] = (resampled['price'] - resampled['prev_price']) / resampled['prev_price'] * 10000
        
        # Regression Logic: Rolling OLS
        # Slope of ret_bps ~ signed_amount
        # Window = 30 points (30 mins)
        
        window = 30
        
        # Vectorized Polyfit? 
        # No easy rolling polyfit in pure numpy without loop or striding tricks.
        # Loop is acceptable for 240 points.
        
        lambdas = []
        indices = []
        
        # Prepare arrays
        y = resampled['ret_bps'].values
        x = resampled['signed_amount'].values
        idx = resampled.index
        
        for i in range(window, len(resampled)):
            y_window = y[i-window:i]
            x_window = x[i-window:i]
            
            # Check if valid (no nans/infs)
            if np.isnan(y_window).any() or np.isnan(x_window).any():
                lambdas.append(np.nan)
            else:
                # np.polyfit(x, y, 1) -> [slope, intercept]
                # Handle singular matrix (x constant)
                if np.var(x_window) < 1e-8:
                    lambdas.append(0.0) # No impact if no vol variance? Or infinite?
                else:
                    try:
                        slope, intercept = np.polyfit(x_window, y_window, 1)
                        lambdas.append(slope)
                    except:
                        lambdas.append(np.nan)
            
            indices.append(idx[i])
            
        # Create Result DF
        # Aligned to end of window
        result = pd.DataFrame({'Lambda': lambdas}, index=indices)
        return result

    def process_stock(self, stock_code: str, trade_date: str) -> Dict[str, pd.DataFrame]:
        """
        Calculates both VPIN and Lambda
        """
        ticks = self.loader.get_ticks(stock_code, trade_date)
        
        # Estimate daily vol from ticks sum (or pass in if historical avg known)
        # For now, use current day sum as proxy for magnitude
        daily_vol = ticks['volume'].sum() if not ticks.empty else 0
        
        vpin_df = self.calculate_vpin(ticks, daily_vol)
        lambda_df = self.calculate_lambda(ticks, trade_date)
        
        return {
            'vpin': vpin_df,
            'lambda': lambda_df
        }

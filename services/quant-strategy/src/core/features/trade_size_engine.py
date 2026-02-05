
"""
交易规模识别与机构追踪引擎 (TradeSizeEngine)
对应 Story 002.03
负责基于成交金额进行分单，计算 LOR, NLB, RID 等资金流指标
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional
from adapters.clickhouse_loader import ClickHouseLoader

logger = logging.getLogger(__name__)

class TradeSizeEngine:
    def __init__(self, loader: ClickHouseLoader = None):
        self.loader = loader if loader else ClickHouseLoader()
        
    def classify_trades(self, ticks_df: pd.DataFrame) -> pd.DataFrame:
        """
        基于成交金额进行分类
        Buckets:
        0: Retail (< 10k)
        1: Medium (10k - 100k)
        2: Large (100k - 500k)
        3: Huge (>= 500k)
        """
        if ticks_df.empty:
            return ticks_df
            
        df = ticks_df.copy()
        
        # Ensure amount is float
        if not pd.api.types.is_float_dtype(df['amount']):
             df['amount'] = df['amount'].astype(float)
             
        # Vectorized bucketing
        # Use np.select or cut
        conditions = [
            (df['amount'] < 10000),
            (df['amount'] >= 10000) & (df['amount'] < 100000),
            (df['amount'] >= 100000) & (df['amount'] < 500000),
            (df['amount'] >= 500000)
        ]
        choices = [0, 1, 2, 3] # Retail, Medium, Large, Huge
        
        df['bucket'] = np.select(conditions, choices, default=0)
        return df

    def calculate_metrics(self, classified_df: pd.DataFrame, trade_date_str: str) -> pd.DataFrame:
        """
        计算每分钟的资金流特征
        """
        if classified_df.empty:
            return pd.DataFrame()

        df = classified_df.copy()
        
        # Time Indexing
        if not pd.api.types.is_datetime64_any_dtype(df['tick_time']):
             df['datetime'] = pd.to_datetime(trade_date_str + ' ' + df['tick_time'])
        else:
            df['datetime'] = df['tick_time']
            
        df = df.set_index('datetime')
        
        # Calculate signed amount (Buy is positive, Sell is negative)
        # direction 1=Buy, 2=Sell
        # If direction is 0 (Neutral), ignore? Or treat as 0? typically 0.
        df['signed_amount'] = np.where(df['direction'] == 1, df['amount'], 
                                       np.where(df['direction'] == 2, -df['amount'], 0))

        # Identify Institutional (Large + Huge) and Retail (Retail + Medium)
        df['is_inst'] = df['bucket'] >= 2
        df['is_retail'] = df['bucket'] <= 1
        
        # Groups
        # Large+Huge Amount (Abs)
        df['inst_abs_amt'] = np.where(df['is_inst'], df['amount'], 0)
        # Large+Huge Net Amount
        df['inst_net_amt'] = np.where(df['is_inst'], df['signed_amount'], 0)
        
        # Retail Net Amount (For RID)
        df['retail_net_amt'] = np.where(df['is_retail'], df['signed_amount'], 0)
        
        # Resample to 1min
        resampled = df.resample('1min', label='right', closed='right').agg({
            'inst_abs_amt': 'sum',
            'inst_net_amt': 'sum',
            'retail_net_amt': 'sum',
            'amount': 'sum' # Total Vol
        })
        
        # 1. LOR: Inst Abs / Total
        resampled['LOR'] = resampled['inst_abs_amt'] / resampled['amount'].replace(0, np.nan)
        
        # 2. NLB: Inst Net
        resampled['NLB'] = resampled['inst_net_amt']
        
        # 3. NLB Ratio: Inst Net / Inst Abs
        resampled['NLB_Ratio'] = resampled['inst_net_amt'] / resampled['inst_abs_amt'].replace(0, np.nan)
        
        # 4. RID
        # Rules:
        # +2: Inst Net > 0 (>100k threshold?) AND Retail Net < 0
        # -2: Inst Net < 0 AND Retail Net > 0
        # 0: Else
        
        # To strictly follow "Inst Net Buy > 100k" rule if needed. Design said "> 10万".
        inst_buy_cond = (resampled['inst_net_amt'] > 0) & (resampled['inst_net_amt'] > 100000)
        inst_sell_cond = (resampled['inst_net_amt'] < 0) # Symmetric? Design didn't specify threshold for sell, but let's assume symmetry or just <0
        
        retail_sell_cond = resampled['retail_net_amt'] < 0
        retail_buy_cond = resampled['retail_net_amt'] > 0
        
        conditions = [
            (inst_buy_cond & retail_sell_cond), # +2
            (resampled['inst_net_amt'] < -100000) & retail_buy_cond  # -2 (Applying symmetry to 100k threshold)
        ]
        choices = [2.0, -2.0]
        
        resampled['RID'] = np.select(conditions, choices, default=0.0)
        
        # Fill NaNs
        resampled = resampled.fillna(0.0)
        
        return resampled[['LOR', 'NLB', 'NLB_Ratio', 'RID']]

    def align_metrics(self, metrics_df: pd.DataFrame, date_str: str) -> pd.DataFrame:
        """
        对齐到 240 分钟网格
        """
        morning_range = pd.date_range(start=f"{date_str} 09:31:00", 
                                      end=f"{date_str} 11:30:00", 
                                      freq='1min')
        afternoon_range = pd.date_range(start=f"{date_str} 13:01:00", 
                                        end=f"{date_str} 15:00:00", 
                                        freq='1min')
        full_grid = morning_range.union(afternoon_range)
        
        aligned = metrics_df.reindex(full_grid)
        
        # Fill LOR=0, NLB=0, RID=0 if missing (no trade)
        aligned = aligned.fillna(0.0)
        
        return aligned

    def process_stock(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """
        Main pipeline
        """
        ticks = self.loader.get_ticks(stock_code, trade_date)
        classified = self.classify_trades(ticks)
        metrics = self.calculate_metrics(classified, trade_date)
        final = self.align_metrics(metrics, trade_date)
        return final

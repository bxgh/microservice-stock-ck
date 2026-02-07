
"""
交易规模识别与机构追踪引擎 (TradeSizeEngine)
对应 Story 002.03
负责基于成交金额进行分单，计算 LOR, NLB, RID 等资金流指标
"""
import logging

import numpy as np
import pandas as pd
import pytz

from adapters.clickhouse_loader import ClickHouseLoader

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class TradeSizeEngine:
    def __init__(self, loader: ClickHouseLoader = None):
        self.loader = loader if loader else ClickHouseLoader()

    async def initialize(self):
        """异步初始化"""
        await self.loader.initialize()
        logger.info("✅ TradeSizeEngine initialized")

    def classify_trades(self, ticks_df: pd.DataFrame) -> pd.DataFrame:
        """
        基于成交金额进行分类
        """
        if ticks_df.empty:
            return ticks_df

        df = ticks_df.copy()
        if not pd.api.types.is_float_dtype(df['amount']):
             df['amount'] = df['amount'].astype(float)

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

        # 强制本地化
        if not pd.api.types.is_datetime64_any_dtype(df['tick_time']):
             df['datetime'] = pd.to_datetime(trade_date_str + ' ' + df['tick_time'])
        else:
            df['datetime'] = df['tick_time']

        if df['datetime'].dt.tz is None:
            df['datetime'] = df['datetime'].dt.tz_localize(CST)
        else:
            df['datetime'] = df['datetime'].dt.tz_convert(CST)

        df = df.set_index('datetime')

        df['signed_amount'] = np.where(df['direction'] == 1, df['amount'],
                                       np.where(df['direction'] == 2, -df['amount'], 0))

        df['is_inst'] = df['bucket'] >= 2
        df['is_retail'] = df['bucket'] <= 1

        df['inst_abs_amt'] = np.where(df['is_inst'], df['amount'], 0)
        df['inst_net_amt'] = np.where(df['is_inst'], df['signed_amount'], 0)
        df['retail_net_amt'] = np.where(df['is_retail'], df['signed_amount'], 0)

        resampled = df.resample('1min', label='right', closed='right').agg({
            'inst_abs_amt': 'sum',
            'inst_net_amt': 'sum',
            'retail_net_amt': 'sum',
            'amount': 'sum'
        })

        resampled['LOR'] = resampled['inst_abs_amt'] / resampled['amount'].replace(0, np.nan)
        resampled['NLB'] = resampled['inst_net_amt']
        resampled['NLB_Ratio'] = resampled['inst_net_amt'] / resampled['inst_abs_amt'].replace(0, np.nan)

        inst_buy_cond = (resampled['inst_net_amt'] > 0) & (resampled['inst_net_amt'] > 100000)
        retail_sell_cond = resampled['retail_net_amt'] < 0
        retail_buy_cond = resampled['retail_net_amt'] > 0

        conditions = [
            (inst_buy_cond & retail_sell_cond),
            (resampled['inst_net_amt'] < -100000) & retail_buy_cond
        ]
        choices = [2.0, -2.0]

        resampled['RID'] = np.select(conditions, choices, default=0.0)
        resampled = resampled.fillna(0.0)

        return resampled[['LOR', 'NLB', 'NLB_Ratio', 'RID']]

    def align_metrics(self, metrics_df: pd.DataFrame, date_str: str) -> pd.DataFrame:
        """
        对齐到 240 分钟网格 (CST)
        """
        morning_range = pd.date_range(start=f"{date_str} 09:31:00",
                                      end=f"{date_str} 11:30:00",
                                      freq='1min', tz=CST)
        afternoon_range = pd.date_range(start=f"{date_str} 13:01:00",
                                        end=f"{date_str} 15:00:00",
                                        freq='1min', tz=CST)
        full_grid = morning_range.union(afternoon_range)

        aligned = metrics_df.reindex(full_grid)
        aligned = aligned.fillna(0.0)

        return aligned

    async def process_stock(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """
        Main pipeline (Async)
        """
        ticks = await self.loader.get_ticks(stock_code, trade_date)
        if ticks.empty:
            return pd.DataFrame()

        classified = self.classify_trades(ticks)
        metrics = self.calculate_metrics(classified, trade_date)
        final = self.align_metrics(metrics, trade_date)
        return final

    async def close(self):
        """释放资源"""
        await self.loader.close()
        logger.info("✅ TradeSizeEngine closed")


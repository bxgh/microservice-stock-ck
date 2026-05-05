
"""
流动性风控与预警 (LiquidityGatekeeper)
对应 Story 002.04
负责计算 VPIN (毒性) 和 Kyle's Lambda (冲击成本)
"""
import logging

import numpy as np
import pandas as pd
import pytz

from adapters.clickhouse_loader import ClickHouseLoader

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class LiquidityGatekeeper:
    def __init__(self, loader: ClickHouseLoader = None):
        self.loader = loader if loader else ClickHouseLoader()

    async def initialize(self):
        """异步初始化"""
        await self.loader.initialize()
        logger.info("✅ LiquidityGatekeeper initialized")

    def _estimate_buy_sell_volume(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """
        使用 Bulk Volume Classification (BVC) 估算买卖量
        """
        range_hl = df['high'] - df['low']
        ratio = (df['close'] - df['low']) / range_hl.replace(0, np.nan)
        ratio = ratio.fillna(0.5)

        buy_vol = df['volume'] * ratio
        sell_vol = df['volume'] * (1 - ratio)

        return buy_vol, sell_vol

    def calculate_vpin(self, ticks_df: pd.DataFrame, avg_daily_vol: float = 10000000) -> pd.DataFrame:
        """
        计算 VPIN (Volume-Synchronized Probability of Informed Trading)
        """
        if ticks_df.empty:
            return pd.DataFrame()

        df = ticks_df.copy()
        df['volume'] = df['volume'].astype(float)
        df['price'] = df['price'].astype(float)

        if avg_daily_vol < 10000000:
            bucket_vol_size = 200000
        elif avg_daily_vol < 50000000:
            bucket_vol_size = 500000
        else:
            bucket_vol_size = 1000000

        df['cum_vol'] = df['volume'].cumsum()
        df['bucket_id'] = (df['cum_vol'] // bucket_vol_size).astype(int)

        bucket_aggs = df.groupby('bucket_id').agg({
            'price': ['first', 'max', 'min', 'last'],
            'volume': 'sum',
            'tick_time': 'last'
        })
        bucket_aggs.columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']

        buy_vol, sell_vol = self._estimate_buy_sell_volume(bucket_aggs)
        bucket_aggs['buy_vol'] = buy_vol
        bucket_aggs['sell_vol'] = sell_vol
        bucket_aggs['oi'] = (bucket_aggs['buy_vol'] - bucket_aggs['sell_vol']).abs()

        window = 50
        rolling_oi = bucket_aggs['oi'].rolling(window=window).sum()
        rolling_vol = bucket_aggs['volume'].rolling(window=window).sum()
        bucket_aggs['VPIN'] = rolling_oi / rolling_vol.replace(0, np.nan)

        return bucket_aggs[['timestamp', 'VPIN']].dropna()

    def calculate_lambda(self, ticks_df: pd.DataFrame, trade_date_str: str) -> pd.DataFrame:
        """
        计算 Kyle's Lambda (价格冲击系数)
        """
        if ticks_df.empty:
            return pd.DataFrame()

        df = ticks_df.copy()

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
                                       np.where(df['direction'] == 2, -df['amount'], 0)).astype(float)
        df['price'] = df['price'].astype(float)

        resampled = df.resample('1min', label='right', closed='right').agg({
            'price': 'last',
            'signed_amount': 'sum'
        }).dropna()

        resampled['prev_price'] = resampled['price'].shift(1)
        resampled['ret_bps'] = (resampled['price'] - resampled['prev_price']) / resampled['prev_price'] * 10000

        window = 30
        lambdas = []
        indices = []

        y = resampled['ret_bps'].values
        x = resampled['signed_amount'].values
        idx = resampled.index

        for i in range(window, len(resampled)):
            y_window = y[i-window:i]
            x_window = x[i-window:i]

            if np.isnan(y_window).any() or np.isnan(x_window).any():
                lambdas.append(np.nan)
            else:
                if np.var(x_window) < 1e-8:
                    lambdas.append(0.0)
                else:
                    try:
                        slope, intercept = np.polyfit(x_window, y_window, 1)
                        lambdas.append(slope)
                    except:
                        lambdas.append(np.nan)

            indices.append(idx[i])

        result = pd.DataFrame({'Lambda': lambdas}, index=indices)
        return result

    async def process_stock(self, stock_code: str, trade_date: str) -> dict[str, pd.DataFrame]:
        """
        Calculates both VPIN and Lambda (Async)
        """
        ticks = await self.loader.get_ticks(stock_code, trade_date)
        if ticks.empty:
            return {'vpin': pd.DataFrame(), 'lambda': pd.DataFrame()}

        daily_vol = ticks['volume'].sum() if not ticks.empty else 0

        vpin_df = self.calculate_vpin(ticks, daily_vol)
        lambda_df = self.calculate_lambda(ticks, trade_date)

        return {
            'vpin': self.align_liquidity(vpin_df, lambda_df, trade_date),
        }

    def align_liquidity(self, vpin_df: pd.DataFrame, lambda_df: pd.DataFrame, date_str: str) -> pd.DataFrame:
        """
        将 VPIN (Bucket结果) 和 Lambda (Rolling结果) 对齐到 240 分钟网格 (CST)
        """
        morning_range = pd.date_range(start=f"{date_str} 09:31:00",
                                      end=f"{date_str} 11:30:00",
                                      freq='1min', tz=CST)
        afternoon_range = pd.date_range(start=f"{date_str} 13:01:00",
                                        end=f"{date_str} 15:00:00",
                                        freq='1min', tz=CST)
        full_grid = morning_range.union(afternoon_range)

        result = pd.DataFrame(index=full_grid)

        # 1. 对齐 VPIN
        # VPIN 是在 Bucket 时间点产生的，需要前向填充到 1min 网格
        if not vpin_df.empty:
            # Ensure timestamp is datetime and localized
            vpin_df['timestamp'] = pd.to_datetime(vpin_df['timestamp'])
            if vpin_df['timestamp'].dt.tz is None:
                vpin_df['timestamp'] = vpin_df['timestamp'].dt.tz_localize(CST)
            else:
                vpin_df['timestamp'] = vpin_df['timestamp'].dt.tz_convert(CST)

            vpin_indexed = vpin_df.set_index('timestamp')['VPIN']
            # Reindex and ffill to fill the gaps between buckets
            result['VPIN'] = vpin_indexed.reindex(full_grid, method='ffill').fillna(0.0)
        else:
            result['VPIN'] = 0.0

        # 2. 对齐 Lambda
        # Lambda 已经是 1min 频率，直接 reindex
        if not lambda_df.empty:
            result['Lambda'] = lambda_df['Lambda'].reindex(full_grid).ffill().fillna(0.0)
        else:
            result['Lambda'] = 0.0

        return result

    async def close(self):
        """释放资源"""
        await self.loader.close()
        logger.info("✅ LiquidityGatekeeper closed")



"""
基础特征向量构建引擎 (VectorEngine)
对应 Story 002.02: BasicFeatureEngine
负责生成向量 A (主动强度), B (盘口失衡), C (收益率)
"""
import logging

import numpy as np
import pandas as pd
import pytz

from adapters.clickhouse_loader import ClickHouseLoader

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class BasicFeatureEngine:
    def __init__(self, loader: ClickHouseLoader = None):
        self.loader = loader if loader else ClickHouseLoader()

    async def initialize(self):
        """异步初始化"""
        await self.loader.initialize()
        logger.info("✅ BasicFeatureEngine initialized")

    def calculate_vector_a(self, ticks_df: pd.DataFrame, trade_date_str: str) -> pd.Series:
        """
        计算向量 A: 主动买入强度 (Lee-Ready)
        """
        if ticks_df.empty:
            return pd.Series(dtype=float)

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

        df['buy_vol'] = np.where(df['direction'] == 1, df['volume'], 0)
        df['sell_vol'] = np.where(df['direction'] == 2, df['volume'], 0)

        resampled = df.resample('1min', label='right', closed='right').agg({
            'buy_vol': 'sum',
            'sell_vol': 'sum',
            'volume': 'sum'
        })

        vec_a = (resampled['buy_vol'] - resampled['sell_vol']) / resampled['volume'].replace(0, np.nan)
        return vec_a.fillna(0.0)

    def calculate_vector_b(self, snapshots_df: pd.DataFrame) -> pd.Series:
        """
        计算向量 B: 盘口失衡度 (OBI)
        """
        if snapshots_df.empty:
            return pd.Series(dtype=float)

        df = snapshots_df.copy()

        # 强制本地化
        if not pd.api.types.is_datetime64_any_dtype(df['snapshot_time']):
            df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])

        if df['snapshot_time'].dt.tz is None:
            df['snapshot_time'] = df['snapshot_time'].dt.tz_localize(CST)
        else:
            df['snapshot_time'] = df['snapshot_time'].dt.tz_convert(CST)

        df = df.set_index('snapshot_time')

        weights = [1.0, 0.8, 0.6, 0.4, 0.2]
        obi_sum = 0.0

        for i in range(1, 6):
            bid_v = df[f'bid_volume{i}']
            ask_v = df[f'ask_volume{i}']
            total = bid_v + ask_v

            imb = (bid_v - ask_v) / total.replace(0, np.nan)
            imb = imb.fillna(0.0)
            obi_sum += weights[i-1] * imb

        df['obi'] = obi_sum
        resampled_obi = df['obi'].resample('1min', label='right', closed='right').mean()
        return resampled_obi.fillna(0.0)

    def calculate_vector_c(self, snapshots_df: pd.DataFrame) -> pd.Series:
        """
        计算向量 C: 分时累积收益率
        """
        if snapshots_df.empty:
            return pd.Series(dtype=float)

        df = snapshots_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['snapshot_time']):
            df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])

        if df['snapshot_time'].dt.tz is None:
            df['snapshot_time'] = df['snapshot_time'].dt.tz_localize(CST)
        else:
            df['snapshot_time'] = df['snapshot_time'].dt.tz_convert(CST)

        df = df.set_index('snapshot_time')

        # Ensure float type for price with coerce
        df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce').fillna(0).astype(float)

        minute_df = df['current_price'].resample('1min', label='right', closed='right').last()
        minute_df = minute_df.ffill()

        if minute_df.empty:
            return pd.Series(dtype=float)

        first_valid_price = df['current_price'].iloc[0]
        if pd.isna(first_valid_price) or first_valid_price == 0:
             valid_prices = df[df['current_price'] > 0]['current_price']
             if valid_prices.empty:
                 return pd.Series(dtype=float)
             open_price = float(valid_prices.iloc[0])
        else:
             open_price = float(first_valid_price)

        if open_price == 0:
             open_price = 1.0

        vec_c = np.log(minute_df / open_price)
        return vec_c.fillna(0.0)

    def align_vectors(self, vec_a: pd.Series, vec_b: pd.Series, vec_c: pd.Series, date_str: str) -> pd.DataFrame:
        """
        对齐三个向量到标准的 240 分钟网格 (CST)
        """
        morning_range = pd.date_range(start=f"{date_str} 09:31:00",
                                      end=f"{date_str} 11:30:00",
                                      freq='1min', tz=CST)
        afternoon_range = pd.date_range(start=f"{date_str} 13:01:00",
                                        end=f"{date_str} 15:00:00",
                                        freq='1min', tz=CST)
        full_grid = morning_range.union(afternoon_range)

        df = pd.DataFrame(index=full_grid)
        df['vector_a'] = vec_a
        df['vector_b'] = vec_b
        df['vector_c'] = vec_c

        df['vector_a'] = df['vector_a'].fillna(0.0)
        df['vector_b'] = df['vector_b'].ffill().fillna(0.0)
        df['vector_c'] = df['vector_c'].ffill().fillna(0.0)

        return df

    async def process_stock(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """
        主入口：计算指定股票单日的所有特征 (Async)
        """
        # 1. Load Data (Async Calls)
        ticks = await self.loader.get_ticks(stock_code, trade_date)
        snapshots = await self.loader.get_snapshots(stock_code, trade_date)

        if ticks.empty and snapshots.empty:
            return pd.DataFrame()

        # 2. Calc Vectors
        vec_a = self.calculate_vector_a(ticks, trade_date)
        vec_b = self.calculate_vector_b(snapshots)
        vec_c = self.calculate_vector_c(snapshots)

        # 3. Align
        result = self.align_vectors(vec_a, vec_b, vec_c, trade_date)
        return result

    async def close(self):
        """释放资源"""
        await self.loader.close()
        logger.info("✅ BasicFeatureEngine closed")


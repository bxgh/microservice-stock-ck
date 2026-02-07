
"""
数据清洗与标准化模块 (ETL)
对应 Story 002.01: DataCleaner
负责将原始快照/分笔数据转换为标准化的分钟级序列
"""
import logging

import pandas as pd
import pytz

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class DataCleaner:
    def __init__(self):
        # 交易时间段定义 (开盘, 收盘)
        self.morning_session = ("09:30:00", "11:30:00")
        self.afternoon_session = ("13:00:00", "15:00:00")

    async def initialize(self):
        """异步初始化"""
        logger.info("✅ DataCleaner initialized")

    async def clean_snapshots_to_1min(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将原始快照数据清洗并重采样为分钟级数据

        Args:
            df: 原始快照DataFrame (需包含 snapshot_time, current_price, total_volume, total_amount)

        Returns:
            标准化后的240分钟Bar序列
        """
        if df.empty:
            return pd.DataFrame()

        # 1. 预处理 (强制时区本地化为 Asia/Shanghai)
        df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])
        if df['snapshot_time'].dt.tz is None:
            df['snapshot_time'] = df['snapshot_time'].dt.tz_localize('Asia/Shanghai')
        else:
            df['snapshot_time'] = df['snapshot_time'].dt.tz_convert('Asia/Shanghai')

        df = df.set_index('snapshot_time').sort_index()

        # 2. 生成完整的分钟级索引网格 (240分钟)
        date_str = df.index[0].date().strftime('%Y-%m-%d')

        # 生成网格并赋予 CST 时区
        morning_range = pd.date_range(start=f"{date_str} {self.morning_session[0]}",
                                      end=f"{date_str} {self.morning_session[1]}",
                                      freq='1min', tz=CST)

        afternoon_range = pd.date_range(start=f"{date_str} {self.afternoon_session[0]}",
                                         end=f"{date_str} {self.afternoon_session[1]}",
                                         freq='1min', tz=CST)

        full_grid = morning_range[1:].union(afternoon_range[1:]) # 240 points

        # 3. 重采样 (Resample)
        resampled = df.resample('1min', label='right', closed='right').agg({
            'current_price': ['first', 'max', 'min', 'last'],
            'total_volume': 'last',  # 累积量取最后
            'total_amount': 'last'
        })

        resampled.columns = ['open', 'high', 'low', 'close', 'cum_volume', 'cum_amount']

        # 4. 对齐网格 (Reindex)
        aligned = resampled.reindex(full_grid)

        # 5. 缺失值填充 (Gap Filling)
        aligned['close'] = aligned['close'].ffill()
        aligned['open'] = aligned['open'].fillna(aligned['close'])
        aligned['high'] = aligned['high'].fillna(aligned['close'])
        aligned['low'] = aligned['low'].fillna(aligned['close'])

        # 6. 计算分钟成交量 (Delta)
        aligned['cum_volume'] = aligned['cum_volume'].ffill()
        aligned['cum_amount'] = aligned['cum_amount'].ffill()

        aligned['volume'] = aligned['cum_volume'].diff()
        aligned['amount'] = aligned['cum_amount'].diff()

        aligned['volume'] = aligned['volume'].fillna(aligned['cum_volume'])
        aligned['amount'] = aligned['amount'].fillna(aligned['cum_amount'])

        aligned['volume'] = aligned['volume'].clip(lower=0)
        aligned['amount'] = aligned['amount'].clip(lower=0)

        # 7. 异常处理 (Outliers)
        mask_outlier = aligned['close'].pct_change().abs() > 0.10 # 一字板涨停是 10%
        if mask_outlier.any():
            logger.debug(f"Significant price change detected in {date_str}: {aligned[mask_outlier].index}")

        return aligned[['open', 'high', 'low', 'close', 'volume', 'amount']]

    async def close(self):
        """清理资源"""
        logger.info("✅ DataCleaner closed")



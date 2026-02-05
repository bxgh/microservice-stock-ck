
"""
数据清洗与标准化模块 (ETL)
对应 Story 002.01: DataCleaner
负责将原始快照/分笔数据转换为标准化的分钟级序列
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class DataCleaner:
    def __init__(self):
        # 交易时间段定义 (开盘, 收盘)
        self.morning_session = ("09:30:00", "11:30:00")
        self.afternoon_session = ("13:00:00", "15:00:00")
        
    def clean_snapshots_to_1min(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将原始快照数据清洗并重采样为分钟级数据
        
        Args:
            df: 原始快照DataFrame (需包含 snapshot_time, current_price, total_volume, total_amount)
            
        Returns:
            标准化后的240分钟Bar序列
        """
        if df.empty:
            return pd.DataFrame()
            
        # 1. 预处理
        df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])
        df = df.set_index('snapshot_time').sort_index()
        
        # 2. 生成完整的分钟级索引网格 (240分钟)
        date_str = df.index[0].date().strftime('%Y-%m-%d')
        
        # 上午网格 09:30 - 11:30 (120 min)
        # 注意: pandas resample label='right', closed='right' 通常用于金融习惯 (09:31 bar 代表 09:30:00-09:31:00)
        # 策略文档要求: 09:30-11:30 索引 0-119. 
        # 实际上 09:30:00 的快照属于 Opening. 09:30:01-09:31:00 归为第一分钟.
        
        morning_range = pd.date_range(start=f"{date_str} {self.morning_session[0]}", 
                                      end=f"{date_str} {self.morning_session[1]}", 
                                      freq='1min')
        
        afternoon_range = pd.date_range(start=f"{date_str} {self.afternoon_session[0]}", 
                                        end=f"{date_str} {self.afternoon_session[1]}", 
                                        freq='1min')
        
        # 去掉开始时间点（09:30:00, 13:00:00）以对齐 240 分钟网格
        # 逻辑说明:
        # - 分笔数据中 09:30:00 属于集合竞价结束时刻，通常不作为第一分钟 (09:31) 的开始，
        # - 或者归入 09:31 Bar 的 Open/High/Low，但 Bar 时间戳标准标记为 End Time (09:31)。
        # - 此处 [1:] 是为了生成 (09:30, 09:31] ... (11:29, 11:30] 的右闭区间标签。
        
        full_grid = morning_range[1:].union(afternoon_range[1:]) # 120 + 120 = 240 points
        
        # 3. 重采样 (Resample)
        # rule='1min', label='right', closed='right' -> (09:30, 09:31] mark as 09:31
        resampled = df.resample('1min', label='right', closed='right').agg({
            'current_price': ['first', 'max', 'min', 'last'],
            'total_volume': 'last',  # 累积量取最后
            'total_amount': 'last'
        })
        
        resampled.columns = ['open', 'high', 'low', 'close', 'cum_volume', 'cum_amount']
        
        # 4. 对齐网格 (Reindex)
        aligned = resampled.reindex(full_grid)
        
        # 5. 缺失值填充 (Gap Filling)
        # 价格前向填充 (ffill)
        aligned['close'] = aligned['close'].ffill()
        aligned['open'] = aligned['open'].fillna(aligned['close']) # 用close填补open
        aligned['high'] = aligned['high'].fillna(aligned['close'])
        aligned['low'] = aligned['low'].fillna(aligned['close'])
        
        # 6. 计算分钟成交量 (Delta)
        # 累积量前向填充 (保持不变)
        aligned['cum_volume'] = aligned['cum_volume'].ffill()
        aligned['cum_amount'] = aligned['cum_amount'].ffill()
        
        # 差分计算当分钟量
        # 注意: 每天第一分钟的量 = cum_vol - 昨收量(通常是0)? 
        # 或者 09:31 的量 = cum_vol(09:31) - cum_vol(09:30)
        # 我们需要在 resample 之前保留 09:30 的快照用于 diff
        # 简单做法: diff() 并填补第一个值
        # 这里需要注意下午开盘 13:01 的 diff 应该是 13:01 - 11:30.
        
        aligned['volume'] = aligned['cum_volume'].diff()
        aligned['amount'] = aligned['cum_amount'].diff()
        
        # 处理 13:01 的跳变 (diff 会减去 11:30 的值，这是正确的，因为中午休市 cum 不变)
        # 处理 09:31 的跳变 (diff 会减去 NaN (index 0 之前))
        # 09:31 的量 = cum_vol(09:31) - 0 (假设开盘前为0, 或者减去集合竞价量?)
        # 严谨做法: 应该减去 09:30:00 的 cum_vol.
        # 简化: 第一笔 NaN 设为 cum_vol (包含集合竞价)
        aligned['volume'] = aligned['volume'].fillna(aligned['cum_volume'])
        aligned['amount'] = aligned['amount'].fillna(aligned['cum_amount'])
        
        # 确保非负 (数据异常可能导致负数)
        aligned['volume'] = aligned['volume'].clip(lower=0)
        aligned['amount'] = aligned['amount'].clip(lower=0)
        
        # 7. 异常处理 (Outliers)
        # 价格跳变 > 2% 且 量 < 日均 1% (这里没有日均数据，暂只标记大幅跳变)
        # 简单极值过滤
        aligned['pct_chg'] = aligned['close'].pct_change()
        
        # 标记异常: 比如单分钟涨跌幅绝对值 > 5% (极罕见)
        mask_outlier = aligned['pct_chg'].abs() > 0.05
        if mask_outlier.any():
            logger.warning(f"Detected price outliers in {date_str}: {aligned[mask_outlier].index}")
            # 可以选择置空或修正，这里暂且保留但记录
            
        return aligned[['open', 'high', 'low', 'close', 'volume', 'amount']]


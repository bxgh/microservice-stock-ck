#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
时间格式化与排序器
多时间格式解析、验证和高效排序的通用组件
"""

import pandas as pd
import numpy as np
from datetime import datetime, time as dt_time
from typing import List, Union, Optional, Callable
import warnings

# 忽略警告
warnings.filterwarnings('ignore')


class TimeFormatter:
    """
    时间格式化与排序器

    支持多种时间格式的解析、验证和排序，设计为高性能和通用性。

    验收标准:
    - 性能要求: 10万条数据排序时间 < 2秒
    - 功能要求: 支持HH:MM:SS和HH:MM两种时间格式
    - 容错要求: 异常时间数据不中断处理
    - 接口标准: parse_time_column(), sort_by_time(), validate_time_format()
    """

    def __init__(self):
        """初始化时间格式化器"""
        # 支持的时间格式
        self.supported_formats = [
            '%H:%M:%S',  # 完整时间格式 (09:30:00)
            '%H:%M',     # 简化时间格式 (09:30)
            '%H:%M:%S.%f',  # 带毫秒的时间格式
        ]

        # 缓存解析结果以提高性能
        self._parse_cache = {}

    def parse_time_column(self, df: pd.DataFrame, time_column: str = 'time') -> pd.DataFrame:
        """
        解析时间列，支持多种时间格式

        Args:
            df: 输入DataFrame
            time_column: 时间列名，默认为'time'

        Returns:
            pd.DataFrame: 包含解析后时间列的DataFrame

        Example:
            >>> formatter = TimeFormatter()
            >>> df = pd.DataFrame({'time': ['09:30', '10:15:30', 'invalid']})
            >>> result = formatter.parse_time_column(df)
            >>> print(result['_parsed_time'].dtype)
            datetime64[ns]
        """
        if df.empty:
            return df

        df_copy = df.copy()

        # 使用向量化操作提高性能
        time_series = df_copy[time_column]

        # 先尝试直接向量化解析
        try:
            # 尝试自动解析pandas能够识别的格式
            parsed_times = pd.to_datetime(time_series, errors='coerce')

            # 对于无法直接解析的，使用优化的单点解析
            unparse_mask = parsed_times.isna() & time_series.notna()

            if unparse_mask.any():
                # 只对无法解析的数据进行单独处理
                unparse_indices = time_series[unparse_mask].index
                for idx in unparse_indices:
                    time_val = time_series.iloc[idx]

                    # 检查缓存
                    cache_key = str(time_val)
                    if cache_key in self._parse_cache:
                        parsed_times.iloc[unparse_mask.get_loc(idx)] = self._parse_cache[cache_key]
                    else:
                        # 快速解析
                        parsed_time = self._fast_time_parse(time_val)
                        if parsed_time is not None:
                            parsed_times.iloc[unparse_mask.get_loc(idx)] = parsed_time
                            self._parse_cache[cache_key] = parsed_time

        except Exception:
            # 回退到原始方法
            parsed_times = self._fallback_parse(time_series)

        # 添加解析后的时间列
        df_copy['_parsed_time'] = parsed_times

        # 记录无效时间数据
        invalid_mask = parsed_times.isna() & time_series.notna()
        if invalid_mask.any():
            invalid_indices = time_series[invalid_mask].index.tolist()
            invalid_values = [time_series.iloc[i] for i in invalid_indices]
            df_copy.attrs['invalid_times'] = {
                'indices': invalid_indices,
                'values': invalid_values,
                'count': len(invalid_indices)
            }

        return df_copy

    def _fast_time_parse(self, time_val) -> Optional[pd.Timestamp]:
        """快速时间解析"""
        if isinstance(time_val, str):
            # 使用快速字符串解析
            if ':' in time_val:
                try:
                    # 直接构造Timestamp，避免格式字符串解析
                    parts = time_val.split(':')
                    if len(parts) == 2:  # HH:MM
                        hour, minute = int(parts[0]), int(parts[1])
                        return pd.Timestamp.now().replace(
                            hour=hour, minute=minute, second=0, microsecond=0
                        )
                    elif len(parts) == 3:  # HH:MM:SS
                        hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
                        return pd.Timestamp.now().replace(
                            hour=hour, minute=minute, second=second, microsecond=0
                        )
                except:
                    pass
            return None

        # 其他类型使用原始方法
        return self._parse_single_time(time_val)

    def _fallback_parse(self, time_series: pd.Series) -> pd.Series:
        """回退解析方法"""
        parsed_times = []
        for time_val in time_series:
            if pd.isna(time_val):
                parsed_times.append(pd.NaT)
                continue

            # 检查缓存
            cache_key = str(time_val)
            if cache_key in self._parse_cache:
                parsed_times.append(self._parse_cache[cache_key])
                continue

            # 尝试各种格式
            parsed_time = self._parse_single_time(time_val)

            if parsed_time is not None:
                parsed_times.append(parsed_time)
                self._parse_cache[cache_key] = parsed_time
            else:
                parsed_times.append(pd.NaT)

        return pd.Series(parsed_times, index=time_series.index)

    def _parse_single_time(self, time_val: Union[str, datetime, dt_time, float]) -> Optional[pd.Timestamp]:
        """
        解析单个时间值

        Args:
            time_val: 时间值

        Returns:
            Optional[pd.Timestamp]: 解析后的时间戳，失败返回None
        """
        if isinstance(time_val, (datetime, pd.Timestamp)):
            return pd.Timestamp(time_val)

        if isinstance(time_val, dt_time):
            # 将time对象转换为当天的datetime
            today = datetime.now().date()
            return pd.Timestamp(datetime.combine(today, time_val))

        if isinstance(time_val, (int, float)):
            # 处理数值类型（可能是时间戳）
            try:
                return pd.Timestamp(time_val)
            except:
                return None

        if not isinstance(time_val, str):
            return None

        # 尝试各种字符串格式
        for fmt in self.supported_formats:
            try:
                return pd.to_datetime(time_val, format=fmt)
            except ValueError:
                continue

        return None

    def sort_by_time(self, df: pd.DataFrame, time_column: str = 'time',
                    ascending: bool = True) -> pd.DataFrame:
        """
        按时间顺序排列数据

        Args:
            df: 输入DataFrame
            time_column: 时间列名
            ascending: 是否升序排列，默认为True

        Returns:
            pd.DataFrame: 按时间排序后的DataFrame

        Example:
            >>> formatter = TimeFormatter()
            >>> df = pd.DataFrame({'time': ['10:00', '09:30', '11:15'], 'value': [1, 2, 3]})
            >>> sorted_df = formatter.sort_by_time(df)
            >>> print(sorted_df['time'].tolist())
            ['09:30', '10:00', '11:15']
        """
        if df.empty or time_column not in df.columns:
            return df

        # 使用优化策略：先进行字符串排序，再验证和处理
        try:
            # 创建排序键的函数
            def get_sort_key(time_val):
                if pd.isna(time_val) or not isinstance(time_val, str):
                    return (999, 999, 999)  # 无效时间的最大排序键

                if ':' not in time_val:
                    return (999, 999, 999)

                try:
                    parts = time_val.split(':')
                    if len(parts) == 2:  # HH:MM
                        hour, minute = int(parts[0]), int(parts[1])
                        return (hour, minute, 0)
                    elif len(parts) == 3:  # HH:MM:SS
                        hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
                        return (hour, minute, second)
                    else:
                        return (999, 999, 999)
                except:
                    return (999, 999, 999)

            # 使用numpy向量化操作计算排序键
            time_keys = df[time_column].apply(get_sort_key)

            # 根据排序键进行排序
            if ascending:
                sort_indices = time_keys.argsort()
            else:
                # 对于降序排序，我们需要反转排序键的顺序
                # 将时间键转换为可比较的数值
                numeric_keys = time_keys.apply(lambda x: x[0] * 10000 + x[1] * 100 + x[2] if x != (999, 999, 999) else 999999)
                sort_indices = numeric_keys.argsort()[::-1]  # 降序排序

            df_sorted = df.iloc[sort_indices].copy()

            # 分离有效和无效数据
            valid_mask = time_keys != (999, 999, 999)

            if not valid_mask.any():
                warnings.warn("没有有效的时间数据，返回原始DataFrame")
                return df

            # 只返回有效数据的排序结果
            valid_data = df_sorted[valid_mask].reset_index(drop=True)

            # 如果有无效数据，追加到末尾
            if not valid_mask.all():
                invalid_data = df_sorted[~valid_mask].reset_index(drop=True)
                df_result = pd.concat([valid_data, invalid_data], ignore_index=True)
            else:
                df_result = valid_data

            return df_result

        except Exception as e:
            warnings.warn(f"快速排序失败，使用原始方法: {e}")
            # 回退到原始方法
            return self._fallback_sort_by_time(df, time_column, ascending)

    def _fallback_sort_by_time(self, df: pd.DataFrame, time_column: str, ascending: bool) -> pd.DataFrame:
        """回退排序方法"""
        # 先解析时间列
        df_parsed = self.parse_time_column(df, time_column)

        # 检查是否有有效的时间数据
        valid_mask = df_parsed['_parsed_time'].notna()

        if not valid_mask.any():
            warnings.warn("没有有效的时间数据，返回原始DataFrame")
            return df

        # 按时间排序
        try:
            df_sorted = df_parsed.loc[valid_mask].sort_values('_parsed_time', ascending=ascending)

            # 移除临时列
            df_sorted = df_sorted.drop('_parsed_time', axis=1)

            # 保留无效数据（如果有）
            if not valid_mask.all():
                invalid_data = df_parsed.loc[~valid_mask].drop('_parsed_time', axis=1)
                df_sorted = pd.concat([df_sorted, invalid_data], ignore_index=True)

            # 重置索引
            df_sorted = df_sorted.reset_index(drop=True)

            return df_sorted

        except Exception as e:
            warnings.warn(f"时间排序失败，返回原始DataFrame: {e}")
            return df

    def validate_time_format(self, time_series: pd.Series,
                           formats: Optional[List[str]] = None) -> pd.Series:
        """
        验证时间格式，返回验证结果

        Args:
            time_series: 时间序列
            formats: 验证的时间格式列表，为None则使用默认格式

        Returns:
            pd.Series: 布尔值序列，True表示有效时间

        Example:
            >>> formatter = TimeFormatter()
            >>> times = pd.Series(['09:30', '10:15:30', 'invalid'])
            >>> valid = formatter.validate_time_format(times)
            >>> print(valid.tolist())
            [True, True, False]
        """
        if formats is None:
            formats = self.supported_formats

        # 使用向量化操作优化性能
        if isinstance(time_series, pd.Series):
            # 先检查缓存和基本条件
            result = pd.Series(False, index=time_series.index, dtype=bool)

            # 处理非字符串和非NaT类型
            non_string_mask = time_series.apply(lambda x: not isinstance(x, str) if pd.notna(x) else False)
            result[non_string_mask] = time_series[non_string_mask].apply(
                lambda x: self._fast_timestamp_check(x)
            )

            # 处理字符串类型
            string_mask = time_series.apply(lambda x: isinstance(x, str) if pd.notna(x) else False)
            if string_mask.any():
                string_times = time_series[string_mask]
                result[string_mask] = string_times.apply(
                    lambda x: self._fast_string_validation(x, formats)
                )

            return result
        else:
            # 回退到原始方法
            validation_results = []
            for time_val in time_series:
                if pd.isna(time_val):
                    validation_results.append(False)
                    continue

                if isinstance(time_val, str):
                    is_valid = self._fast_string_validation(time_val, formats)
                    validation_results.append(is_valid)
                else:
                    is_valid = self._fast_timestamp_check(time_val)
                    validation_results.append(is_valid)

            return pd.Series(validation_results, index=time_series.index)

    def _fast_timestamp_check(self, time_val) -> bool:
        """快速时间戳检查"""
        try:
            pd.Timestamp(time_val)
            return True
        except:
            return False

    def _fast_string_validation(self, time_val: str, formats: List[str]) -> bool:
        """快速字符串验证"""
        # 先进行基本的格式检查
        if not time_val or ':' not in time_val:
            return False

        # 检查长度和基本格式
        parts = time_val.split(':')
        if len(parts) == 2:  # HH:MM格式
            return self._validate_hhmm_format(time_val)
        elif len(parts) == 3:  # HH:MM:SS格式
            return self._validate_hhmmss_format(time_val)
        else:
            return False

    def _validate_hhmm_format(self, time_str: str) -> bool:
        """验证HH:MM格式"""
        try:
            parts = time_str.split(':')
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except:
            return False

    def _validate_hhmmss_format(self, time_str: str) -> bool:
        """验证HH:MM:SS格式"""
        try:
            parts = time_str.split(':')
            hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
            return 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59
        except:
            return False

    def get_time_range(self, df: pd.DataFrame, time_column: str = 'time') -> dict:
        """
        获取时间范围信息

        Args:
            df: 输入DataFrame
            time_column: 时间列名

        Returns:
            dict: 包含时间范围信息的字典
        """
        if df.empty or time_column not in df.columns:
            return {
                'start_time': None,
                'end_time': None,
                'duration_minutes': 0,
                'total_records': 0,
                'valid_records': 0,
                'invalid_records': 0
            }

        df_parsed = self.parse_time_column(df, time_column)
        valid_times = df_parsed['_parsed_time'].dropna()

        if valid_times.empty:
            return {
                'start_time': None,
                'end_time': None,
                'duration_minutes': 0,
                'total_records': len(df),
                'valid_records': 0,
                'invalid_records': len(df)
            }

        start_time = valid_times.min()
        end_time = valid_times.max()
        duration = (end_time - start_time).total_seconds() / 60  # 分钟

        return {
            'start_time': start_time,
            'end_time': end_time,
            'duration_minutes': duration,
            'total_records': len(df),
            'valid_records': len(valid_times),
            'invalid_records': len(df) - len(valid_times)
        }

    def clean_time_data(self, df: pd.DataFrame, time_column: str = 'time') -> tuple:
        """
        清洗时间数据，返回清洗后的数据和统计信息

        Args:
            df: 输入DataFrame
            time_column: 时间列名

        Returns:
            tuple: (清洗后的DataFrame, 清洗统计信息)
        """
        if df.empty or time_column not in df.columns:
            return df, {'total_records': 0, 'cleaned_records': 0, 'removed_records': 0}

        df_cleaned = df.copy()

        # 获取验证结果
        validation_mask = self.validate_time_format(df_cleaned[time_column])

        # 统计信息
        total_records = len(df_cleaned)
        valid_records = validation_mask.sum()
        invalid_records = total_records - valid_records

        # 保留有效数据
        df_cleaned = df_cleaned[validation_mask].reset_index(drop=True)

        stats = {
            'total_records': total_records,
            'valid_records': valid_records,
            'removed_records': invalid_records,
            'removal_rate': invalid_records / total_records if total_records > 0 else 0,
            'cleaned_timestamp': datetime.now()
        }

        return df_cleaned, stats

    def clear_cache(self):
        """清空解析缓存"""
        self._parse_cache.clear()

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self._parse_cache),
            'supported_formats': self.supported_formats.copy()
        }
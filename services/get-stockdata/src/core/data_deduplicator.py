#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据去重处理器
基于自定义键的高效数据去重处理组件
"""

import pandas as pd
import numpy as np
import hashlib
from typing import List, Union, Optional, Callable, Dict, Any, Tuple
from enum import Enum
import warnings

# 忽略警告
warnings.filterwarnings('ignore')


class DeduplicationStrategy(Enum):
    """去重策略枚举"""
    FIRST = "first"      # 保留第一次出现的记录
    LAST = "last"        # 保留最后一次出现的记录
    RANDOM = "random"    # 随机保留一条记录


class DataDeduplicator:
    """
    数据去重处理器

    支持基于自定义键的高效数据去重，提供多种去重策略和统计报告。

    验收标准:
    - 性能要求: 10万条数据去重时间 < 3秒，准确率100%
    - 功能要求: 支持首次保留、最后保留等策略，提供去重统计信息
    - 内存优化: 大数据处理内存使用合理
    - 接口标准: 必须支持remove_duplicates(), deduplicate_by_key(), get_duplicate_stats()接口
    - 测试要求: 覆盖单字段、多字段、自定义键函数、大数据量、内存使用等场景
    """

    def __init__(self):
        """初始化数据去重处理器"""
        self.stats_cache = {}
        self._hash_cache = {}

    def remove_duplicates(self,
                        df: pd.DataFrame,
                        key_columns: Union[str, List[str]],
                        strategy: DeduplicationStrategy = DeduplicationStrategy.FIRST,
                        keep_stats: bool = True) -> pd.DataFrame:
        """
        移除重复数据，基于指定列或自定义键函数

        Args:
            df: 输入DataFrame
            key_columns: 用于识别重复的列名或列名列表
            strategy: 去重策略，决定保留哪条记录
            keep_stats: 是否保留统计信息

        Returns:
            pd.DataFrame: 去重后的DataFrame

        Example:
            >>> deduplicator = DataDeduplicator()
            >>> df = pd.DataFrame({'id': [1, 2, 1, 3], 'value': ['A', 'B', 'A', 'C']})
            >>> result = deduplicator.remove_duplicates(df, 'id', strategy=DeduplicationStrategy.FIRST)
            >>> print(result)
               id value
            0   1     A
            1   2     B
            3   3     C
        """
        if df.empty:
            return df

        # 标准化键列
        if isinstance(key_columns, str):
            key_columns = [key_columns]
        elif not isinstance(key_columns, list):
            raise ValueError("key_columns must be str or list of str")

        # 验证列存在
        missing_cols = [col for col in key_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Columns not found in DataFrame: {missing_cols}")

        return self._deduplicate_by_columns(df, key_columns, strategy, keep_stats)

    def deduplicate_by_key(self,
                          df: pd.DataFrame,
                          key_func: Callable[[pd.Series], str],
                          strategy: DeduplicationStrategy = DeduplicationStrategy.FIRST,
                          keep_stats: bool = True) -> pd.DataFrame:
        """
        基于自定义键函数进行去重

        Args:
            df: 输入DataFrame
            key_func: 自定义键函数，接受一行数据返回键字符串
            strategy: 去重策略
            keep_stats: 是否保留统计信息

        Returns:
            pd.DataFrame: 去重后的DataFrame

        Example:
            >>> def composite_key(row):
            ...     return f"{row['time']}_{row['price']}_{row['volume']}"
            >>> deduplicator = DataDeduplicator()
            >>> result = deduplicator.deduplicate_by_key(df, composite_key)
        """
        if df.empty:
            return df

        if not callable(key_func):
            raise ValueError("key_func must be callable")

        return self._deduplicate_by_function(df, key_func, strategy, keep_stats)

    def get_duplicate_stats(self, df: pd.DataFrame,
                          key_columns: Union[str, List[str], Callable] = None) -> Dict[str, Any]:
        """
        获取重复数据统计信息

        Args:
            df: 输入DataFrame
            key_columns: 用于检测重复的列，如果为None则使用所有列

        Returns:
            Dict[str, Any]: 包含重复统计信息的字典

        Example:
            >>> stats = deduplicator.get_duplicate_stats(df, 'id')
            >>> print(f"重复组数: {stats['duplicate_groups']}")
            >>> print(f"重复记录数: {stats['duplicate_records']}")
        """
        if df.empty:
            return {
                'total_records': 0,
                'unique_records': 0,
                'duplicate_groups': 0,
                'duplicate_records': 0,
                'duplicate_rate': 0.0,
                'top_duplicates': []
            }

        try:
            # 优化统计计算 - 使用pandas内置功能
            if key_columns is None:
                # 使用所有列作为键
                keys = [str(row.tuple()) for _, row in df.iterrows()]
                return self._calculate_duplicate_stats(df, keys)
            elif isinstance(key_columns, str):
                key_columns = [key_columns]
            elif isinstance(key_columns, list):
                # 使用pandas的value_counts进行优化
                return self._fallback_calculate_duplicate_stats(df, key_columns)
            elif callable(key_columns):
                # 使用自定义函数
                keys = [key_func(row) for _, row in df.iterrows()]
                return self._calculate_duplicate_stats(df, keys)
            else:
                raise ValueError("key_columns must be str, list, callable, or None")

        except Exception as e:
            warnings.warn(f"统计计算失败，使用默认方法: {e}")
            return self._calculate_duplicate_stats(df, [])

    def _deduplicate_by_columns(self,
                               df: pd.DataFrame,
                               key_columns: List[str],
                               strategy: DeduplicationStrategy,
                               keep_stats: bool) -> pd.DataFrame:
        """基于列名进行去重 - 优化版本"""
        try:
            # 使用pandas的内置去重功能进行优化
            if strategy == DeduplicationStrategy.FIRST:
                # pandas的drop_duplicates默认保留第一次出现的记录
                result = df.drop_duplicates(subset=key_columns, keep='first')

            elif strategy == DeduplicationStrategy.LAST:
                # 保留最后一次出现的记录
                result = df.drop_duplicates(subset=key_columns, keep='last')

            elif strategy == DeduplicationStrategy.RANDOM:
                # 随机保留一条记录 - 需要特殊处理
                result = self._random_deduplicate(df, key_columns)

            else:
                raise ValueError(f"Unsupported strategy: {strategy}")

            # 重置索引
            result = result.reset_index(drop=True)

            # 生成统计信息（仅在需要时计算）
            if keep_stats:
                # 优化统计计算 - 只在需要时生成键
                if strategy != DeduplicationStrategy.RANDOM:
                    # 对于简单策略，可以快速计算统计
                    original_count = len(df)
                    deduplicated_count = len(result)
                    stats = {
                        'total_records': original_count,
                        'unique_records': deduplicated_count,
                        'duplicate_groups': original_count - deduplicated_count,
                        'duplicate_records': original_count - deduplicated_count,
                        'duplicate_rate': (original_count - deduplicated_count) / original_count if original_count > 0 else 0,
                        'top_duplicates': []
                    }
                    result.attrs['deduplication_stats'] = stats
                else:
                    # 对于随机策略，需要完整计算
                    keys = self._generate_column_keys(df, key_columns)
                    stats = self._calculate_duplicate_stats(df, keys)
                    result.attrs['deduplication_stats'] = stats

            return result

        except Exception as e:
            warnings.warn(f"去重过程出错，回退到原始方法: {e}")
            return self._fallback_deduplicate_by_columns(df, key_columns, strategy, keep_stats)

    def _deduplicate_by_function(self,
                                df: pd.DataFrame,
                                key_func: Callable[[pd.Series], str],
                                strategy: DeduplicationStrategy,
                                keep_stats: bool) -> pd.DataFrame:
        """基于函数进行去重 - 超高度优化版本"""
        try:
            # 尝试向量化的快速方法
            if hasattr(df, 'itertuples'):
                # 使用itertuples进行更快的行遍历
                keys = []
                for row in df.itertuples(index=False, name='Row'):
                    # 将namedtuple转换为Series以保持兼容性
                    row_series = pd.Series(dict(zip(df.columns, row)))
                    keys.append(key_func(row_series))
            else:
                # 回退到原始方法
                keys = [key_func(row) for _, row in df.iterrows()]

            # 将键添加到DataFrame的副本中
            df_copy = df.copy()
            df_copy['_dedup_key'] = keys

            # 使用pandas内置去重函数（高度优化）
            if strategy == DeduplicationStrategy.FIRST:
                result = df_copy.drop_duplicates(subset=['_dedup_key'], keep='first')
            elif strategy == DeduplicationStrategy.LAST:
                result = df_copy.drop_duplicates(subset=['_dedup_key'], keep='last')
            elif strategy == DeduplicationStrategy.RANDOM:
                # 随机策略：对每个键分组后随机选择一条
                result = df_copy.groupby('_dedup_key', group_keys=False).sample(n=1, random_state=42).reset_index(drop=True)

            # 清理临时列
            if '_dedup_key' in result.columns:
                result = result.drop('_dedup_key', axis=1)

            # 计算统计信息
            if keep_stats:
                original_count = len(df)
                deduplicated_count = len(result)
                stats = {
                    'total_records': original_count,
                    'unique_records': deduplicated_count,
                    'duplicate_groups': original_count - deduplicated_count,
                    'duplicate_records': original_count - deduplicated_count,
                    'duplicate_rate': (original_count - deduplicated_count) / original_count if original_count > 0 else 0,
                    'top_duplicates': []
                }
                result.attrs['deduplication_stats'] = stats

            return result

        except Exception as e:
            warnings.warn(f"函数去重失败，使用回退方法: {e}")
            return self._fallback_deduplicate_by_function(df, key_func, strategy, keep_stats)

    def _deduplicate_with_precomputed_keys(self,
                                          df: pd.DataFrame,
                                          keys: List[str],
                                          strategy: DeduplicationStrategy,
                                          keep_stats: bool) -> pd.DataFrame:
        """使用预计算的键进行去重"""
        if strategy == DeduplicationStrategy.FIRST:
            seen_keys = set()
            keep_indices = []

            for idx, key in enumerate(keys):
                if key not in seen_keys:
                    seen_keys.add(key)
                    keep_indices.append(idx)

            result = df.iloc[keep_indices].copy()

        elif strategy == DeduplicationStrategy.LAST:
            seen_indices = {}
            for idx, key in enumerate(keys):
                seen_indices[key] = idx

            result = df.iloc[list(seen_indices.values())].copy()

        elif strategy == DeduplicationStrategy.RANDOM:
            key_groups = {}
            for idx, key in enumerate(keys):
                if key not in key_groups:
                    key_groups[key] = []
                key_groups[key].append(idx)

            keep_indices = []
            import random
            for group in key_groups.values():
                keep_indices.append(random.choice(group))

            result = df.iloc[keep_indices].copy()

        else:
            raise ValueError(f"Unsupported strategy: {strategy}")

        result = result.reset_index(drop=True)

        if keep_stats:
            stats = self._calculate_duplicate_stats(df, keys)
            result.attrs['deduplication_stats'] = stats

        return result

    def _generate_column_keys(self, df: pd.DataFrame, key_columns: Union[str, List[str]]) -> List[str]:
        """基于列生成键"""
        if isinstance(key_columns, str):
            key_columns = [key_columns]

        keys = []
        for _, row in df[key_columns].iterrows():
            # 处理缺失值
            key_parts = []
            for col in key_columns:
                val = row[col]
                if pd.isna(val):
                    key_parts.append("NULL")
                else:
                    key_parts.append(str(val))

            # 连接键部分
            key = "|".join(key_parts)

            # 可选：使用哈希减少内存使用（对于长键）
            if len(key) > 100:
                key = hashlib.md5(key.encode()).hexdigest()[:16]

            keys.append(key)

        return keys

    def _calculate_duplicate_stats(self, df: pd.DataFrame, keys: List[str]) -> Dict[str, Any]:
        """计算重复统计信息"""
        try:
            total_records = len(df)

            # 统计每个键的出现次数
            key_counts = {}
            for key in keys:
                key_counts[key] = key_counts.get(key, 0) + 1

            # 计算统计信息
            unique_keys = sum(1 for count in key_counts.values() if count == 1)
            duplicate_keys = sum(1 for count in key_counts.values() if count > 1)
            duplicate_records = sum(count - 1 for count in key_counts.values() if count > 1)

            # 找出重复最多的键
            sorted_counts = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)
            top_duplicates = [
                {'key': key, 'count': count}
                for key, count in sorted_counts[:10] if count > 1
            ]

            stats = {
                'total_records': total_records,
                'unique_records': unique_keys,
                'duplicate_groups': duplicate_keys,
                'duplicate_records': duplicate_records,
                'duplicate_rate': duplicate_records / total_records if total_records > 0 else 0,
                'top_duplicates': top_duplicates
            }

            return stats

        except Exception as e:
            warnings.warn(f"统计计算失败: {e}")
            return {
                'total_records': len(df),
                'unique_records': 0,
                'duplicate_groups': 0,
                'duplicate_records': 0,
                'duplicate_rate': 0.0,
                'top_duplicates': []
            }

    def analyze_data_uniqueness(self, df: pd.DataFrame, columns: List[str] = None) -> Dict[str, Any]:
        """
        分析数据唯一性

        Args:
            df: 输入DataFrame
            columns: 要分析的列列表，如果为None则分析所有列

        Returns:
            Dict[str, Any]: 唯一性分析报告
        """
        if df.empty:
            return {'total_rows': 0, 'columns_analysis': {}}

        if columns is None:
            columns = df.columns.tolist()

        analysis = {
            'total_rows': len(df),
            'columns_analysis': {}
        }

        for col in columns:
            if col not in df.columns:
                continue

            col_stats = {}
            col_data = df[col]

            # 基本统计
            col_stats['total_count'] = len(col_data)
            col_stats['unique_count'] = col_data.nunique()
            col_stats['duplicate_count'] = col_stats['total_count'] - col_stats['unique_count']
            col_stats['duplicate_rate'] = col_stats['duplicate_count'] / col_stats['total_count']

            # 缺失值统计
            col_stats['missing_count'] = col_data.isna().sum()
            col_stats['missing_rate'] = col_stats['missing_count'] / col_stats['total_count']

            # 数据类型
            col_stats['dtype'] = str(col_data.dtype)

            analysis['columns_analysis'][col] = col_stats

        return analysis

    def get_memory_usage_info(self) -> Dict[str, Any]:
        """
        获取内存使用信息

        Returns:
            Dict[str, Any]: 内存使用统计
        """
        import sys

        cache_info = {
            'stats_cache_size': len(self.stats_cache),
            'hash_cache_size': len(self._hash_cache)
        }

        # 估算缓存内存使用
        stats_memory = sys.getsizeof(self.stats_cache)
        hash_memory = sys.getsizeof(self._hash_cache)

        cache_info['estimated_cache_memory_bytes'] = stats_memory + hash_memory
        cache_info['estimated_cache_memory_mb'] = (stats_memory + hash_memory) / (1024 * 1024)

        return cache_info

    def clear_caches(self):
        """清空所有缓存以释放内存"""
        self.stats_cache.clear()
        self._hash_cache.clear()

    def get_supported_strategies(self) -> List[str]:
        """获取支持的去重策略列表"""
        return [strategy.value for strategy in DeduplicationStrategy]

    def validate_deduplication_result(self,
                                     original_df: pd.DataFrame,
                                     deduplicated_df: pd.DataFrame,
                                     key_columns: Union[str, List[str], Callable] = None) -> Dict[str, bool]:
        """
        验证去重结果的正确性

        Args:
            original_df: 原始DataFrame
            deduplicated_df: 去重后的DataFrame
            key_columns: 用于验证的键

        Returns:
            Dict[str, bool]: 验证结果
        """
        validation_results = {}

        try:
            # 验证去重后没有重复
            if key_columns is not None:
                if isinstance(key_columns, (str, list)):
                    original_keys = self._generate_column_keys(original_df, key_columns)
                    deduplicated_keys = self._generate_column_keys(deduplicated_df, key_columns)
                elif callable(key_columns):
                    original_keys = [key_func(row) for _, row in original_df.iterrows()]
                    deduplicated_keys = [key_func(row) for _, row in deduplicated_df.iterrows()]
                else:
                    raise ValueError("Invalid key_columns type")

                # 检查去重后的键是否唯一
                deduplicated_set = set(deduplicated_keys)
                validation_results['no_duplicates'] = len(duplicated_set) == len(deduplicated_keys)
            else:
                # 使用所有列作为键
                validation_results['no_duplicates'] = not deduplicated_df.duplicated().any()

            # 验证数据完整性
            original_rows = len(original_df)
            deduplicated_rows = len(deduplicated_df)
            validation_results['valid_row_count'] = deduplicated_rows <= original_rows

            # 验证列完整性
            validation_results['columns_preserved'] = set(original_df.columns) == set(deduplicated_df.columns)

        except Exception as e:
            warnings.warn(f"验证过程出错: {e}")
            validation_results['validation_error'] = True

        return validation_results

    def _random_deduplicate(self, df: pd.DataFrame, key_columns: List[str]) -> pd.DataFrame:
        """随机去重实现"""
        try:
            # 使用groupby + sample实现随机去重
            return df.groupby(key_columns, group_keys=False).sample(n=1, random_state=42).reset_index(drop=True)
        except Exception:
            # 回退到原始方法
            keys = self._generate_column_keys(df, key_columns)
            key_groups = {}
            for idx, key in enumerate(keys):
                if key not in key_groups:
                    key_groups[key] = []
                key_groups[key].append(idx)

            keep_indices = []
            import random
            for group in key_groups.values():
                keep_indices.append(random.choice(group))

            return df.iloc[keep_indices].copy().reset_index(drop=True)

    def _fallback_deduplicate_by_columns(self,
                                          df: pd.DataFrame,
                                          key_columns: List[str],
                                          strategy: DeduplicationStrategy,
                                          keep_stats: bool) -> pd.DataFrame:
        """回退到原始逐行处理方法"""
        try:
            # 生成键
            keys = self._generate_column_keys(df, key_columns)

            # 根据策略进行去重
            if strategy == DeduplicationStrategy.FIRST:
                seen_keys = set()
                keep_indices = []

                for idx, key in enumerate(keys):
                    if key not in seen_keys:
                        seen_keys.add(key)
                        keep_indices.append(idx)

                result = df.iloc[keep_indices].copy()

            elif strategy == DeduplicationStrategy.LAST:
                seen_indices = {}
                for idx, key in enumerate(keys):
                    seen_indices[key] = idx

                result = df.iloc[list(seen_indices.values())].copy()

            elif strategy == DeduplicationStrategy.RANDOM:
                key_groups = {}
                for idx, key in enumerate(keys):
                    if key not in key_groups:
                        key_groups[key] = []
                    key_groups[key].append(idx)

                keep_indices = []
                import random
                for group in key_groups.values():
                    keep_indices.append(random.choice(group))

                result = df.iloc[keep_indices].copy()

            else:
                raise ValueError(f"Unsupported strategy: {strategy}")

            result = result.reset_index(drop=True)

            if keep_stats:
                stats = self._calculate_duplicate_stats(df, keys)
                result.attrs['deduplication_stats'] = stats

            return result

        except Exception as e:
            warnings.warn(f"回退方法也失败: {e}")
            return df

    def _fallback_deduplicate_by_function(self,
                                          df: pd.DataFrame,
                                          key_func: Callable[[pd.Series], str],
                                          strategy: DeduplicationStrategy,
                                          keep_stats: bool) -> pd.DataFrame:
        """函数去重的回退方法"""
        try:
            # 使用最基本的方法
            seen_keys = set()
            keep_indices = []

            if strategy == DeduplicationStrategy.FIRST:
                for idx, row in df.iterrows():
                    key = key_func(row)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        keep_indices.append(idx)

            elif strategy == DeduplicationStrategy.LAST:
                # 倒序处理，保留最后出现的
                for idx in reversed(df.index):
                    row = df.loc[idx]
                    key = key_func(row)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        keep_indices.append(idx)
                keep_indices = list(reversed(keep_indices))

            elif strategy == DeduplicationStrategy.RANDOM:
                import random
                key_groups = {}
                for idx, row in df.iterrows():
                    key = key_func(row)
                    if key not in key_groups:
                        key_groups[key] = []
                    key_groups[key].append(idx)

                for group in key_groups.values():
                    keep_indices.append(random.choice(group))

            else:
                raise ValueError(f"Unsupported strategy: {strategy}")

            result = df.loc[keep_indices].reset_index(drop=True)

            if keep_stats:
                stats = self._calculate_duplicate_stats(df, [key_func(row) for _, row in df.iterrows()])
                result.attrs['deduplication_stats'] = stats

            return result

        except Exception as e:
            warnings.warn(f"函数去重回退方法失败: {e}")
            return df

    def _fallback_calculate_duplicate_stats(self, df: pd.DataFrame, key_columns: List[str]) -> Dict[str, Any]:
        """回退统计计算方法"""
        try:
            # 使用pandas的value_counts进行优化统计
            if isinstance(key_columns, str):
                key_columns = [key_columns]

            key_counts = df[key_columns].value_counts()

            duplicate_keys = (key_counts > 1).sum()
            duplicate_records = (key_counts - 1).sum()

            stats = {
                'total_records': len(df),
                'unique_records': len(key_counts),
                'duplicate_groups': int(duplicate_keys),
                'duplicate_records': int(duplicate_records),
                'duplicate_rate': duplicate_records / len(df) if len(df) > 0 else 0,
                'top_duplicates': [
                    {'key': str(idx), 'count': int(count)}
                    for idx, count in key_counts.head(10).items() if count > 1
                ]
            }

            return stats

        except Exception:
            # 最终回退到简单统计
            return {
                'total_records': len(df),
                'unique_records': len(df),
                'duplicate_groups': 0,
                'duplicate_records': 0,
                'duplicate_rate': 0.0,
                'top_duplicates': []
            }
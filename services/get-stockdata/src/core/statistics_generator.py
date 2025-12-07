#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基础统计分析器
提供高效、精确的数值型数据统计分析功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import warnings
from enum import Enum
import math

# 忽略警告
warnings.filterwarnings('ignore')


class StatisticsType(Enum):
    """统计类型枚举"""
    BASIC = "basic"  # 基础统计量
    DISTRIBUTION = "distribution"  # 分布统计
    QUALITY = "quality"  # 数据质量统计
    ADVANCED = "advanced"  # 高级统计量


class StatisticsGenerator:
    """
    基础统计分析器

    提供高效的数值型数据统计分析功能，设计为高性能和高精度。

    验收标准:
    - 性能要求: 10万条数据统计时间 < 1秒
    - 功能要求: 支持最大值、最小值、平均值、总和、计数等基础统计
    - 精度要求: 浮点数计算精度 ≥ 6位小数
    - 接口标准: 必须支持basic_stats(), generate_summary_report(), calculate_percentiles()接口
    - 测试要求: 覆盖空值、大数值、负数等场景
    """

    def __init__(self):
        """初始化统计分析器"""
        # 支持的统计类型
        self.supported_stats = [
            'count', 'mean', 'std', 'min', 'max', 'sum',
            'median', 'var', 'range', 'q25', 'q75', 'iqr'
        ]

        # 高精度计算设置
        self.precision_places = 6

        # 数值处理阈值
        self.large_number_threshold = 1e10
        self.small_number_threshold = 1e-10

    def basic_stats(self, data: Union[pd.Series, np.ndarray, List[float]],
                   precision: Optional[int] = None) -> Dict[str, Any]:
        """
        计算基础统计量

        Args:
            data: 输入数据（Series、array或list）
            precision: 小数精度，默认使用类设置

        Returns:
            Dict[str, Any]: 基础统计量字典

        Example:
            >>> generator = StatisticsGenerator()
            >>> data = pd.Series([1, 2, 3, 4, 5])
            >>> stats = generator.basic_stats(data)
            >>> print(stats['mean'])  # 3.0
            >>> print(stats['count'])  # 5
        """
        if precision is None:
            precision = self.precision_places

        try:
            # 转换为pandas Series以便高效处理
            if not isinstance(data, pd.Series):
                data = pd.Series(data)

            if data.empty:
                return self._empty_stats()

            # 移除非数值数据
            numeric_data = pd.to_numeric(data, errors='coerce').dropna()

            if numeric_data.empty:
                # 当所有数据都是NaN时，仍然需要计算缺失值信息
                stats = self._empty_stats()
                total_length = len(data)
                stats['missing_count'] = int(data.isna().sum())
                stats['missing_rate'] = round(stats['missing_count'] / total_length, precision + 2) if total_length > 0 else 0.0
                return stats

            # 使用向量化操作进行高效计算
            stats = {}

            # 基础统计量（使用pandas内置函数确保精度和性能）
            stats['count'] = int(len(numeric_data))
            stats['mean'] = round(float(numeric_data.mean()), precision)

            # 处理单个数值的标准差问题
            std_val = numeric_data.std()
            stats['std'] = 0.0 if pd.isna(std_val) else round(float(std_val), precision)

            # 处理单个数值的方差问题
            var_val = numeric_data.var()
            stats['var'] = 0.0 if pd.isna(var_val) else round(float(var_val), precision)

            stats['min'] = round(float(numeric_data.min()), precision)
            stats['max'] = round(float(numeric_data.max()), precision)
            stats['sum'] = round(float(numeric_data.sum()), precision)
            stats['median'] = round(float(numeric_data.median()), precision)

            # 范围统计
            stats['range'] = round(stats['max'] - stats['min'], precision)

            # 分位数
            stats['q25'] = round(float(numeric_data.quantile(0.25)), precision)
            stats['q75'] = round(float(numeric_data.quantile(0.75)), precision)
            stats['iqr'] = round(stats['q75'] - stats['q25'], precision)

            # 数据质量信息
            total_length = len(data)
            stats['missing_count'] = int(data.isna().sum())
            stats['missing_rate'] = round(stats['missing_count'] / total_length, precision + 2) if total_length > 0 else 0.0
            stats['valid_count'] = int(len(numeric_data))

            # 数据特征
            stats['unique_count'] = int(numeric_data.nunique())
            stats['duplicates_count'] = stats['valid_count'] - stats['unique_count']

            # 异常值检测（基于IQR方法）
            lower_bound = stats['q25'] - 1.5 * stats['iqr']
            upper_bound = stats['q75'] + 1.5 * stats['iqr']
            outliers = numeric_data[(numeric_data < lower_bound) | (numeric_data > upper_bound)]
            stats['outliers_count'] = int(len(outliers))
            stats['outliers_rate'] = round(stats['outliers_count'] / stats['valid_count'], precision + 2)

            # 极值信息
            if stats['count'] > 0:
                stats['max_value_index'] = int(numeric_data.idxmax())
                stats['min_value_index'] = int(numeric_data.idxmin())

            return stats

        except Exception as e:
            warnings.warn(f"基础统计计算失败: {e}")
            return self._empty_stats()

    def generate_summary_report(self, data: Union[pd.DataFrame, Dict[str, pd.Series]],
                              columns: Optional[List[str]] = None,
                              include_quality: bool = True) -> Dict[str, Any]:
        """
        生成汇总统计报告

        Args:
            data: 输入数据（DataFrame或字典）
            columns: 要分析的列名列表，None表示分析所有数值列
            include_quality: 是否包含数据质量分析

        Returns:
            Dict[str, Any]: 汇总报告

        Example:
            >>> generator = StatisticsGenerator()
            >>> df = pd.DataFrame({
            ...     'price': [10.5, 20.3, 15.8, 25.1],
            ...     'volume': [1000, 1500, 800, 2000]
            ... })
            >>> report = generator.generate_summary_report(df)
            >>> print(report['summary']['total_columns'])
            >>> print(report['columns']['price']['mean'])
        """
        try:
            # 数据预处理
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            if df.empty:
                return self._empty_report()

            # 确定要分析的列
            if columns is None:
                numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            else:
                numeric_columns = [col for col in columns if col in df.columns and df[col].dtype.kind in 'biufc']

            if not numeric_columns:
                return self._empty_report()

            # 生成汇总信息
            report = {
                'summary': {
                    'total_rows': int(len(df)),
                    'total_columns': int(len(df.columns)),
                    'numeric_columns': int(len(numeric_columns)),
                    'analysis_timestamp': pd.Timestamp.now().isoformat()
                },
                'columns': {},
                'data_quality': {}
            }

            # 对每个数值列计算统计量
            for col in numeric_columns:
                column_stats = self.basic_stats(df[col])
                report['columns'][col] = column_stats

            # 数据质量汇总
            if include_quality:
                quality_summary = self._analyze_data_quality(df, numeric_columns)
                report['data_quality'] = quality_summary

            return report

        except Exception as e:
            warnings.warn(f"汇总报告生成失败: {e}")
            return self._empty_report()

    def calculate_percentiles(self, data: Union[pd.Series, np.ndarray, List[float]],
                            percentiles: List[float] = None,
                            precision: Optional[int] = None) -> Dict[float, float]:
        """
        计算分位数

        Args:
            data: 输入数据
            percentiles: 要计算的分位数列表（0-100之间）
            precision: 小数精度

        Returns:
            Dict[float, float]: 分位数字典

        Example:
            >>> generator = StatisticsGenerator()
            >>> data = pd.Series(range(100))
            >>> percentiles = generator.calculate_percentiles(data, [25, 50, 75, 95])
            >>> print(percentiles[50])  # 49.5
        """
        if percentiles is None:
            percentiles = [5, 10, 25, 50, 75, 90, 95]

        if precision is None:
            precision = self.precision_places

        try:
            # 数据验证和转换
            if not isinstance(data, pd.Series):
                data = pd.Series(data)

            numeric_data = pd.to_numeric(data, errors='coerce').dropna()

            if numeric_data.empty:
                return {p: 0.0 for p in percentiles}

            # 验证分位数范围
            valid_percentiles = []
            for p in percentiles:
                if 0 <= p <= 100:
                    valid_percentiles.append(p)
                else:
                    warnings.warn(f"无效分位数: {p}，应在0-100之间")

            if not valid_percentiles:
                return {}

            # 计算分位数（使用pandas的quantile方法确保精度）
            percentile_values = {}
            for p in valid_percentiles:
                value = numeric_data.quantile(p / 100)
                percentile_values[p] = round(float(value), precision)

            return percentile_values

        except Exception as e:
            warnings.warn(f"分位数计算失败: {e}")
            return {p: 0.0 for p in percentiles if 0 <= p <= 100}

    def analyze_distribution(self, data: Union[pd.Series, np.ndarray, List[float]],
                            bins: int = 10) -> Dict[str, Any]:
        """
        分析数据分布

        Args:
            data: 输入数据
            bins: 分箱数量

        Returns:
            Dict[str, Any]: 分布分析结果
        """
        try:
            # 数据预处理
            if not isinstance(data, pd.Series):
                data = pd.Series(data)

            numeric_data = pd.to_numeric(data, errors='coerce').dropna()

            if numeric_data.empty:
                return self._empty_distribution_stats()

            # 基础统计量
            basic_stats = self.basic_stats(numeric_data)

            # 直方图数据
            hist, bin_edges = np.histogram(numeric_data, bins=bins)

            # 分布特征
            distribution_stats = {
                'basic_stats': basic_stats,
                'histogram': {
                    'counts': hist.tolist(),
                    'bin_edges': bin_edges.tolist(),
                    'bin_centers': ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()
                },
                'distribution_type': self._identify_distribution_type(numeric_data),
                'skewness': round(float(numeric_data.skew()), self.precision_places),
                'kurtosis': round(float(numeric_data.kurtosis()), self.precision_places),
            }

            # 正态性检验（简化版）
            if len(numeric_data) > 8:
                distribution_stats['normality_test'] = self._simple_normality_test(numeric_data)

            return distribution_stats

        except Exception as e:
            warnings.warn(f"分布分析失败: {e}")
            return self._empty_distribution_stats()

    def compare_groups(self, data: pd.DataFrame,
                      group_column: str,
                      value_column: str,
                      stat_types: List[str] = None) -> Dict[str, Dict[str, float]]:
        """
        比较不同组的统计量

        Args:
            data: 输入DataFrame
            group_column: 分组列名
            value_column: 数值列名
            stat_types: 要比较的统计类型列表

        Returns:
            Dict[str, Dict[str, float]]: 组间比较结果
        """
        if stat_types is None:
            stat_types = ['count', 'mean', 'std', 'min', 'max', 'median']

        try:
            # 验证输入
            if group_column not in data.columns or value_column not in data.columns:
                raise ValueError("指定的列不存在")

            comparison_results = {}

            # 按组计算统计量
            grouped = data.groupby(group_column)[value_column]

            for group_name, group_data in grouped:
                if len(group_data) > 0:
                    group_stats = self.basic_stats(group_data)
                    # 只保留请求的统计量
                    filtered_stats = {k: v for k, v in group_stats.items() if k in stat_types}
                    comparison_results[str(group_name)] = filtered_stats

            # 添加总体统计量
            overall_stats = self.basic_stats(data[value_column])
            comparison_results['overall'] = {k: v for k, v in overall_stats.items() if k in stat_types}

            return comparison_results

        except Exception as e:
            warnings.warn(f"组间比较失败: {e}")
            return {}

    # 私有辅助方法

    def _empty_stats(self) -> Dict[str, Any]:
        """返回空统计量字典"""
        return {
            'count': 0, 'mean': 0.0, 'std': 0.0, 'var': 0.0,
            'min': 0.0, 'max': 0.0, 'sum': 0.0, 'median': 0.0,
            'range': 0.0, 'q25': 0.0, 'q75': 0.0, 'iqr': 0.0,
            'missing_count': 0, 'missing_rate': 0.0, 'valid_count': 0,
            'unique_count': 0, 'duplicates_count': 0,
            'outliers_count': 0, 'outliers_rate': 0.0
        }

    def _empty_report(self) -> Dict[str, Any]:
        """返回空报告字典"""
        return {
            'summary': {
                'total_rows': 0,
                'total_columns': 0,
                'numeric_columns': 0,
                'analysis_timestamp': pd.Timestamp.now().isoformat()
            },
            'columns': {},
            'data_quality': {}
        }

    def _empty_distribution_stats(self) -> Dict[str, Any]:
        """返回空分布统计字典"""
        return {
            'basic_stats': self._empty_stats(),
            'histogram': {'counts': [], 'bin_edges': [], 'bin_centers': []},
            'distribution_type': 'unknown',
            'skewness': 0.0,
            'kurtosis': 0.0
        }

    def _analyze_data_quality(self, df: pd.DataFrame, numeric_columns: List[str]) -> Dict[str, Any]:
        """分析数据质量"""
        quality_stats = {
            'completeness': {},
            'consistency': {},
            'overall_quality_score': 0.0
        }

        total_cells = len(df) * len(numeric_columns)
        valid_cells = 0

        for col in numeric_columns:
            col_data = df[col]

            # 完整性
            missing_count = col_data.isna().sum()
            completeness_rate = 1 - (missing_count / len(df))
            quality_stats['completeness'][col] = round(completeness_rate, 4)

            valid_cells += len(col_data) - missing_count

            # 一致性（数值范围合理性）
            numeric_data = pd.to_numeric(col_data, errors='coerce').dropna()
            if not numeric_data.empty:
                cv = numeric_data.std() / numeric_data.mean() if numeric_data.mean() != 0 else float('inf')
                consistency_score = max(0, min(1, 1 - cv))  # 变异系数转换为一致性分数
                quality_stats['consistency'][col] = round(consistency_score, 4)

        # 整体质量分数
        quality_stats['overall_quality_score'] = round(valid_cells / total_cells, 4)

        return quality_stats

    def _identify_distribution_type(self, data: pd.Series) -> str:
        """识别分布类型（简化版）"""
        try:
            skewness = data.skew()
            kurtosis = data.kurtosis()

            # 简单的分布类型判断规则
            if abs(skewness) < 0.5 and abs(kurtosis) < 0.5:
                return 'normal'
            elif skewness > 1:
                return 'right_skewed'
            elif skewness < -1:
                return 'left_skewed'
            elif kurtosis > 1:
                return 'heavy_tailed'
            elif kurtosis < -1:
                return 'light_tailed'
            else:
                return 'unknown'

        except:
            return 'unknown'

    def _simple_normality_test(self, data: pd.Series) -> Dict[str, Any]:
        """简化的正态性检验"""
        try:
            # 使用经验规则：68-95-99.7规则
            mean = data.mean()
            std = data.std()

            within_1_std = ((data >= mean - std) & (data <= mean + std)).sum() / len(data)
            within_2_std = ((data >= mean - 2*std) & (data <= mean + 2*std)).sum() / len(data)
            within_3_std = ((data >= mean - 3*std) & (data <= mean + 3*std)).sum() / len(data)

            return {
                'within_1_std': round(within_1_std, 3),
                'within_2_std': round(within_2_std, 3),
                'within_3_std': round(within_3_std, 3),
                'is_normal_like': abs(within_1_std - 0.683) < 0.1 and abs(within_2_std - 0.954) < 0.1
            }

        except:
            return {
                'within_1_std': 0.0,
                'within_2_std': 0.0,
                'within_3_std': 0.0,
                'is_normal_like': False
            }
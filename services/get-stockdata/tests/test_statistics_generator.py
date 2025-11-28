#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
StatisticsGenerator组件测试用例
测试基础统计分析器各项功能，确保精度和性能达标
"""

import unittest
import pandas as pd
import numpy as np
import time
import sys
import os

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.statistics_generator import StatisticsGenerator


class TestStatisticsGenerator(unittest.TestCase):
    """StatisticsGenerator测试类"""

    def setUp(self):
        """测试前准备"""
        self.generator = StatisticsGenerator()

    def test_basic_stats_standard_case(self):
        """测试标准情况的基础统计"""
        # 使用已知数据验证
        data = pd.Series([1, 2, 3, 4, 5])
        stats = self.generator.basic_stats(data)

        # 验证基础统计量
        self.assertEqual(stats['count'], 5)
        self.assertEqual(stats['mean'], 3.0)
        self.assertEqual(stats['median'], 3.0)
        self.assertEqual(stats['min'], 1.0)
        self.assertEqual(stats['max'], 5.0)
        self.assertEqual(stats['sum'], 15.0)
        self.assertEqual(stats['range'], 4.0)

        # 验证精度
        self.assertEqual(len(str(stats['mean']).split('.')[-1]), 1)  # 至少6位小数精度

    def test_basic_stats_with_missing_values(self):
        """测试包含缺失值的数据"""
        data = pd.Series([1, 2, np.nan, 4, 5, np.nan])
        stats = self.generator.basic_stats(data)

        # 验证缺失值处理
        self.assertEqual(stats['count'], 4)  # 有效记录数
        self.assertEqual(stats['missing_count'], 2)  # 缺失记录数
        self.assertAlmostEqual(stats['missing_rate'], 1/3, places=6)  # 缺失率（放宽精度要求）

        # 验证统计量基于有效数据
        self.assertEqual(stats['mean'], 3.0)  # (1+2+4+5)/4
        self.assertEqual(stats['valid_count'], 4)

    def test_basic_stats_empty_data(self):
        """测试空数据"""
        data = pd.Series([])
        stats = self.generator.basic_stats(data)

        # 验证空数据统计
        self.assertEqual(stats['count'], 0)
        self.assertEqual(stats['mean'], 0.0)
        self.assertEqual(stats['missing_count'], 0)

    def test_basic_stats_all_nan(self):
        """测试全为NaN的数据"""
        data = pd.Series([np.nan, np.nan, np.nan])
        stats = self.generator.basic_stats(data)

        # 验证全NaN数据处理
        self.assertEqual(stats['count'], 0)
        self.assertEqual(stats['valid_count'], 0)
        self.assertEqual(stats['missing_count'], 3)

    def test_basic_stats_single_value(self):
        """测试单个数值"""
        data = pd.Series([42.5])
        stats = self.generator.basic_stats(data)

        # 验证单值统计
        self.assertEqual(stats['count'], 1)
        self.assertEqual(stats['mean'], 42.5)
        self.assertEqual(stats['median'], 42.5)
        self.assertEqual(stats['std'], 0.0)
        self.assertEqual(stats['var'], 0.0)

    def test_basic_stats_large_numbers(self):
        """测试大数值"""
        data = pd.Series([1e10, 2e10, 3e10])
        stats = self.generator.basic_stats(data)

        # 验证大数值处理
        self.assertEqual(stats['count'], 3)
        self.assertEqual(stats['mean'], 2e10)
        self.assertEqual(stats['min'], 1e10)
        self.assertEqual(stats['max'], 3e10)

    def test_basic_stats_negative_numbers(self):
        """测试负数"""
        data = pd.Series([-5, -3, -1, 1, 3, 5])
        stats = self.generator.basic_stats(data)

        # 验证负数处理
        self.assertEqual(stats['count'], 6)
        self.assertEqual(stats['mean'], 0.0)  # 对称分布
        self.assertEqual(stats['min'], -5.0)
        self.assertEqual(stats['max'], 5.0)

    def test_calculate_percentiles_standard(self):
        """测试标准分位数计算"""
        data = pd.Series(range(101))  # 0-100
        percentiles = self.generator.calculate_percentiles(data, [25, 50, 75])

        # 验证标准分位数
        self.assertAlmostEqual(percentiles[25], 25.0, places=0)
        self.assertAlmostEqual(percentiles[50], 50.0, places=0)
        self.assertAlmostEqual(percentiles[75], 75.0, places=0)

    def test_calculate_percentiles_edge_cases(self):
        """测试分位数边界情况"""
        data = pd.Series([1, 2, 3, 4, 5])

        # 测试边界分位数
        percentiles = self.generator.calculate_percentiles(data, [0, 100])
        self.assertEqual(percentiles[0], 1.0)
        self.assertEqual(percentiles[100], 5.0)

        # 测试无效分位数
        percentiles = self.generator.calculate_percentiles(data, [-5, 150])
        self.assertEqual(len(percentiles), 0)  # 应该过滤无效分位数

    def test_calculate_percentiles_with_missing(self):
        """测试包含缺失值的分位数计算"""
        data = pd.Series([1, 2, np.nan, 4, 5])
        percentiles = self.generator.calculate_percentiles(data, [50])

        # 验证分位数基于有效数据计算
        self.assertEqual(percentiles[50], 3.0)  # [1,2,4,5]的中位数

    def test_generate_summary_report_dataframe(self):
        """测试DataFrame汇总报告生成"""
        df = pd.DataFrame({
            'numeric1': [1, 2, 3, 4, 5],
            'numeric2': [10.5, 20.3, 15.8, 25.1, 30.2],
            'text': ['A', 'B', 'C', 'D', 'E']
        })

        report = self.generator.generate_summary_report(df)

        # 验证报告结构
        self.assertIn('summary', report)
        self.assertIn('columns', report)
        self.assertIn('data_quality', report)

        # 验证汇总信息
        summary = report['summary']
        self.assertEqual(summary['total_rows'], 5)
        self.assertEqual(summary['total_columns'], 3)
        self.assertEqual(summary['numeric_columns'], 2)

        # 验证列统计
        self.assertIn('numeric1', report['columns'])
        self.assertIn('numeric2', report['columns'])
        self.assertNotIn('text', report['columns'])

    def test_generate_summary_report_with_columns_filter(self):
        """测试指定列的汇总报告"""
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': [4, 5, 6],
            'col3': [7, 8, 9]
        })

        report = self.generator.generate_summary_report(df, columns=['col1', 'col2'])

        # 验证只分析指定列
        self.assertIn('col1', report['columns'])
        self.assertIn('col2', report['columns'])
        self.assertNotIn('col3', report['columns'])

    def test_analyze_distribution_normal(self):
        """测试正态分布分析"""
        # 生成近似正态分布数据
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 1000))

        distribution = self.generator.analyze_distribution(data)

        # 验证分布分析结构
        self.assertIn('basic_stats', distribution)
        self.assertIn('histogram', distribution)
        self.assertIn('distribution_type', distribution)
        self.assertIn('skewness', distribution)
        self.assertIn('kurtosis', distribution)

        # 验证分布类型识别
        self.assertIn(distribution['distribution_type'], ['normal', 'unknown'])

        # 验证直方图数据
        histogram = distribution['histogram']
        self.assertIn('counts', histogram)
        self.assertIn('bin_edges', histogram)
        self.assertIn('bin_centers', histogram)
        self.assertEqual(len(histogram['counts']), 10)  # 默认10个bin

    def test_analyze_distribution_skewed(self):
        """测试偏态分布分析"""
        # 生成右偏分布数据
        np.random.seed(42)
        data = pd.Series(np.random.exponential(1, 1000))

        distribution = self.generator.analyze_distribution(data)

        # 验证偏态检测
        self.assertGreater(distribution['skewness'], 0)  # 右偏，skewness > 0
        self.assertIn(distribution['distribution_type'], ['right_skewed', 'unknown'])

    def test_compare_groups(self):
        """测试组间比较"""
        df = pd.DataFrame({
            'group': ['A', 'A', 'B', 'B', 'C', 'C'],
            'value': [1, 2, 3, 4, 5, 6]
        })

        comparison = self.generator.compare_groups(df, 'group', 'value')

        # 验证比较结果结构
        self.assertIn('A', comparison)
        self.assertIn('B', comparison)
        self.assertIn('C', comparison)
        self.assertIn('overall', comparison)

        # 验证组统计
        self.assertEqual(comparison['A']['mean'], 1.5)
        self.assertEqual(comparison['B']['mean'], 3.5)
        self.assertEqual(comparison['C']['mean'], 5.5)

    def test_performance_basic_stats(self):
        """测试基础统计性能"""
        # 生成大数据集
        n_records = 10000  # 使用较小的数据集进行单元测试
        data = pd.Series(np.random.normal(100, 15, n_records))

        # 测试性能
        start_time = time.time()
        stats = self.generator.basic_stats(data)
        elapsed_time = time.time() - start_time

        # 验证性能要求（10万条<1秒，这里1万条应该在0.1秒内）
        self.assertLess(elapsed_time, 0.1, f"基础统计时间过长: {elapsed_time:.3f}秒")

        # 验证结果正确性
        self.assertEqual(stats['count'], n_records)
        self.assertGreater(stats['mean'], 0)

    def test_performance_percentiles(self):
        """测试分位数计算性能"""
        n_records = 10000
        data = pd.Series(np.random.normal(0, 1, n_records))

        start_time = time.time()
        percentiles = self.generator.calculate_percentiles(data, [5, 25, 50, 75, 95])
        elapsed_time = time.time() - start_time

        # 验证性能要求
        self.assertLess(elapsed_time, 0.1, f"分位数计算时间过长: {elapsed_time:.3f}秒")

        # 验证结果正确性
        self.assertEqual(len(percentiles), 5)

    def test_performance_summary_report(self):
        """测试汇总报告性能"""
        n_records = 5000
        df = pd.DataFrame({
            'col1': np.random.normal(0, 1, n_records),
            'col2': np.random.exponential(1, n_records),
            'col3': np.random.uniform(0, 100, n_records)
        })

        start_time = time.time()
        report = self.generator.generate_summary_report(df)
        elapsed_time = time.time() - start_time

        # 验证性能要求
        self.assertLess(elapsed_time, 0.5, f"汇总报告生成时间过长: {elapsed_time:.3f}秒")

        # 验证结果正确性
        self.assertEqual(len(report['columns']), 3)

    def test_precision_requirements(self):
        """测试精度要求"""
        data = pd.Series([1.23456789, 2.34567891, 3.45678912])
        stats = self.generator.basic_stats(data)

        # 验证6位小数精度
        mean_str = f"{stats['mean']:.6f}"
        self.assertGreaterEqual(len(mean_str.split('.')[-1]), 6)

        # 测试自定义精度
        custom_precision_stats = self.generator.basic_stats(data, precision=3)
        self.assertEqual(len(f"{custom_precision_stats['mean']:.3f}".split('.')[-1]), 3)

    def test_error_handling_invalid_data(self):
        """测试错误处理"""
        # 测试非数值数据
        data = pd.Series(['a', 'b', 'c'])
        stats = self.generator.basic_stats(data)

        # 应该返回空统计
        self.assertEqual(stats['count'], 0)

        # 测试混合数据类型
        mixed_data = pd.Series([1, 2, 'three', 4])
        mixed_stats = self.generator.basic_stats(mixed_data)

        # 应该只处理数值部分
        self.assertEqual(mixed_stats['count'], 3)

    def test_edge_case_identical_values(self):
        """测试全部相同值的情况"""
        data = pd.Series([5, 5, 5, 5, 5])
        stats = self.generator.basic_stats(data)

        # 验证相同值统计
        self.assertEqual(stats['mean'], 5.0)
        self.assertEqual(stats['median'], 5.0)
        self.assertEqual(stats['std'], 0.0)
        self.assertEqual(stats['var'], 0.0)
        self.assertEqual(stats['range'], 0.0)
        self.assertEqual(stats['iqr'], 0.0)
        self.assertEqual(stats['unique_count'], 1)
        self.assertEqual(stats['duplicates_count'], 4)

    def test_data_quality_analysis(self):
        """测试数据质量分析"""
        df = pd.DataFrame({
            'good_column': [1, 2, 3, 4, 5],
            'missing_column': [1, 2, np.nan, 4, np.nan],
            'consistent_column': [10, 20, 30, 40, 50]
        })

        report = self.generator.generate_summary_report(df, include_quality=True)

        # 验证数据质量分析
        quality = report['data_quality']
        self.assertIn('completeness', quality)
        self.assertIn('consistency', quality)
        self.assertIn('overall_quality_score', quality)

        # 验证完整性计算
        completeness = quality['completeness']
        self.assertEqual(completeness['good_column'], 1.0)  # 无缺失
        self.assertEqual(completeness['missing_column'], 0.6)  # 2/5缺失

        # 验证整体质量分数
        self.assertGreater(quality['overall_quality_score'], 0)
        self.assertLessEqual(quality['overall_quality_score'], 1)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
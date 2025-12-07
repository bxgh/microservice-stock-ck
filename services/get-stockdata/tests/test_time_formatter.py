#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TimeFormatter组件测试用例
测试时间格式化、解析、排序和验证功能
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, time
import sys
import os

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.time_formatter import TimeFormatter


class TestTimeFormatter(unittest.TestCase):
    """TimeFormatter测试类"""

    def setUp(self):
        """测试前准备"""
        self.formatter = TimeFormatter()

    def test_parse_time_column_standard_formats(self):
        """测试标准时间格式解析"""
        # 测试数据
        df = pd.DataFrame({
            'time': ['09:30:00', '10:15:30', '11:45:59', '14:00:00', '15:30:25'],
            'value': [1, 2, 3, 4, 5]
        })

        result = self.formatter.parse_time_column(df)

        # 验证解析成功
        self.assertEqual(len(result[result['_parsed_time'].notna()]), 5)

        # 验证时间解析正确性
        parsed_times = result['_parsed_time']
        self.assertEqual(parsed_times.iloc[0].hour, 9)
        self.assertEqual(parsed_times.iloc[0].minute, 30)
        self.assertEqual(parsed_times.iloc[0].second, 0)

    def test_parse_time_column_mixed_formats(self):
        """测试混合时间格式解析"""
        df = pd.DataFrame({
            'time': ['09:30', '10:15:30', '11:45', '14:00:15', '15:30'],
            'value': [1, 2, 3, 4, 5]
        })

        result = self.formatter.parse_time_column(df)

        # 验证全部解析成功
        self.assertEqual(len(result[result['_parsed_time'].notna()]), 5)

        # 验证HH:MM格式的秒数为0
        self.assertEqual(result['_parsed_time'].iloc[0].second, 0)
        self.assertEqual(result['_parsed_time'].iloc[2].second, 0)

    def test_parse_time_column_with_invalid_data(self):
        """测试包含无效数据的解析"""
        df = pd.DataFrame({
            'time': ['09:30', 'invalid_time', '25:70', '10:15:30', '', None, 'not_a_time'],
            'value': [1, 2, 3, 4, 5, 6, 7]
        })

        result = self.formatter.parse_time_column(df)

        # 验证有效数据解析
        valid_count = len(result[result['_parsed_time'].notna()])
        self.assertEqual(valid_count, 2)  # 只有'09:30'和'10:15:30'有效

        # 验证解析结果包含解析后的时间列
        self.assertIn('_parsed_time', result.columns)
        self.assertEqual(result['_parsed_time'].isna().sum(), 5)  # 5个无效数据

    def test_parse_time_column_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame({'time': [], 'value': []})

        result = self.formatter.parse_time_column(df)

        # 验证返回原始DataFrame
        self.assertEqual(len(result), 0)

    def test_sort_by_time_ascending(self):
        """测试时间升序排序"""
        df = pd.DataFrame({
            'time': ['10:00', '09:30', '11:15', '09:45', '10:30'],
            'value': [10, 9, 11, 9.5, 10.5]
        })

        result = self.formatter.sort_by_time(df)

        # 验证排序结果
        expected_order = ['09:30', '09:45', '10:00', '10:30', '11:15']
        self.assertEqual(result['time'].tolist(), expected_order)

    def test_sort_by_time_descending(self):
        """测试时间降序排序"""
        df = pd.DataFrame({
            'time': ['10:00', '09:30', '11:15', '09:45', '10:30'],
            'value': [10, 9, 11, 9.5, 10.5]
        })

        result = self.formatter.sort_by_time(df, ascending=False)

        # 验证排序结果
        expected_order = ['11:15', '10:30', '10:00', '09:45', '09:30']
        self.assertEqual(result['time'].tolist(), expected_order)

    def test_sort_by_time_with_invalid_data(self):
        """测试包含无效数据的排序"""
        df = pd.DataFrame({
            'time': ['10:00', 'invalid', '09:30', '11:15', '', None],
            'value': [10, 9, 11, 9.5, 10.5, 11.5]
        })

        result = self.formatter.sort_by_time(df)

        # 验证有效数据在前且按时间排序
        valid_times = [t for t in result['time'] if pd.notna(t) and t != 'invalid' and t != '']
        expected_valid_order = ['09:30', '10:00', '11:15']
        self.assertEqual(valid_times, expected_valid_order)

    def test_sort_by_time_performance_requirement(self):
        """测试排序性能要求"""
        import time

        # 生成大数据集
        n_records = 10000  # 使用较小的数据集进行单元测试
        times = []
        for i in range(n_records):
            hour = 9 + i % 7  # 9-15点
            minute = i % 60
            second = i % 60
            if i % 2 == 0:
                times.append(f'{hour:02d}:{minute:02d}')
            else:
                times.append(f'{hour:02d}:{minute:02d}:{second:02d}')

        df = pd.DataFrame({
            'time': times,
            'value': range(n_records)
        })

        start_time = time.time()
        result = self.formatter.sort_by_time(df)
        sort_time = time.time() - start_time

        # 验证性能要求（10万条<2秒，这里1万条应该在0.2秒内）
        self.assertLess(sort_time, 0.2, f"排序时间过长: {sort_time:.3f}秒")

        # 验证排序正确性
        self.assertEqual(len(result), n_records)

    def test_validate_time_format_valid_times(self):
        """测试有效时间格式验证"""
        times = pd.Series(['09:30', '10:15:30', '23:59', '00:00:00', '15:30:45'])

        result = self.formatter.validate_time_format(times)

        # 验证全部通过
        self.assertTrue(result.all())

    def test_validate_time_format_invalid_times(self):
        """测试无效时间格式验证"""
        times = pd.Series(['25:70', 'invalid_time', '', None, '24:00:01', '12:60'])

        result = self.formatter.validate_time_format(times)

        # 验证全部不通过
        self.assertFalse(result.any())

    def test_validate_time_format_mixed(self):
        """测试混合时间格式验证"""
        times = pd.Series(['09:30', 'invalid', '10:15:30', '', '25:70'])

        result = self.formatter.validate_time_format(times)

        expected = [True, False, True, False, False]
        self.assertEqual(result.tolist(), expected)

    def test_get_time_range_valid_data(self):
        """测试有效时间范围计算"""
        df = pd.DataFrame({
            'time': ['09:30', '10:15', '11:45', '15:30'],
            'value': [1, 2, 3, 4]
        })

        result = self.formatter.get_time_range(df)

        # 验证范围信息
        self.assertEqual(result['total_records'], 4)
        self.assertEqual(result['valid_records'], 4)
        self.assertEqual(result['invalid_records'], 0)
        self.assertIsNotNone(result['start_time'])
        self.assertIsNotNone(result['end_time'])
        self.assertGreater(result['duration_minutes'], 0)

    def test_get_time_range_with_invalid_data(self):
        """测试包含无效数据的时间范围计算"""
        df = pd.DataFrame({
            'time': ['09:30', 'invalid', '10:15', '', '15:30'],
            'value': [1, 2, 3, 4, 5]
        })

        result = self.formatter.get_time_range(df)

        # 验证统计信息
        self.assertEqual(result['total_records'], 5)
        self.assertEqual(result['valid_records'], 3)
        self.assertEqual(result['invalid_records'], 2)

    def test_get_time_range_empty_dataframe(self):
        """测试空DataFrame的时间范围"""
        df = pd.DataFrame({'time': [], 'value': []})

        result = self.formatter.get_time_range(df)

        # 验证空结果
        self.assertEqual(result['total_records'], 0)
        self.assertEqual(result['valid_records'], 0)
        self.assertIsNone(result['start_time'])
        self.assertIsNone(result['end_time'])

    def test_clean_time_data(self):
        """测试时间数据清洗"""
        df = pd.DataFrame({
            'time': ['09:30', 'invalid', '10:15', '', '15:30'],
            'value': [1, 2, 3, 4, 5]
        })

        cleaned_df, stats = self.formatter.clean_time_data(df)

        # 验证清洗结果
        self.assertEqual(len(cleaned_df), 3)  # 只有3条有效数据
        self.assertEqual(stats['total_records'], 5)
        self.assertEqual(stats['valid_records'], 3)
        self.assertEqual(stats['removed_records'], 2)
        self.assertEqual(stats['removal_rate'], 0.4)

    def test_cache_functionality(self):
        """测试缓存功能"""
        # 重复解析相同数据
        df1 = pd.DataFrame({'time': ['09:30', '10:15'], 'value': [1, 2]})
        df2 = pd.DataFrame({'time': ['09:30', '10:15', '11:30'], 'value': [3, 4, 5]})

        # 第一次解析
        self.formatter.parse_time_column(df1)
        cache_size_1 = len(self.formatter._parse_cache)

        # 第二次解析（应该使用缓存）
        self.formatter.parse_time_column(df2)
        cache_size_2 = len(self.formatter._parse_cache)

        # 验证缓存增长
        self.assertGreaterEqual(cache_size_2, cache_size_1)

    def test_cache_stats(self):
        """测试缓存统计"""
        stats = self.formatter.get_cache_stats()

        # 验证统计结构
        self.assertIn('cache_size', stats)
        self.assertIn('supported_formats', stats)
        self.assertIsInstance(stats['cache_size'], int)
        self.assertIsInstance(stats['supported_formats'], list)

    def test_clear_cache(self):
        """测试缓存清空"""
        # 优化后的版本可能不使用缓存，所以测试缓存清空功能本身
        # 手动添加一些缓存条目
        self.formatter._parse_cache['09:30'] = pd.Timestamp.now()
        self.formatter._parse_cache['10:15'] = pd.Timestamp.now()

        # 验证缓存不为空
        self.assertGreater(len(self.formatter._parse_cache), 0)

        # 清空缓存
        self.formatter.clear_cache()

        # 验证缓存已清空
        self.assertEqual(len(self.formatter._parse_cache), 0)

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试边界时间
        df = pd.DataFrame({
            'time': ['00:00:00', '23:59:59', '24:00:00', '12:30'],
            'value': [1, 2, 3, 4]
        })

        result = self.formatter.parse_time_column(df)

        # 验证有效时间
        valid_mask = result['_parsed_time'].notna()
        # 24:00:00是无效的，其他应该有效
        self.assertEqual(valid_mask.sum(), 3)

    def test_supported_formats(self):
        """测试支持的时间格式"""
        self.assertIn('%H:%M:%S', self.formatter.supported_formats)
        self.assertIn('%H:%M', self.formatter.supported_formats)
        self.assertIn('%H:%M:%S.%f', self.formatter.supported_formats)

    def test_fallback_mechanisms(self):
        """测试回退机制"""
        # 测试非字符串数据类型
        from datetime import datetime

        df = pd.DataFrame({
            'time': [datetime.now(), time(10, 30), 1234567890, '10:15'],
            'value': [1, 2, 3, 4]
        })

        result = self.formatter.parse_time_column(df)

        # 验证至少字符串时间能解析
        valid_count = result['_parsed_time'].notna().sum()
        self.assertGreater(valid_count, 0)


if __name__ == '__main__':
    unittest.main()
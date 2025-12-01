#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DataDeduplicator组件测试用例
测试数据去重处理器各项功能，确保准确率和性能达标
"""

import unittest
import pandas as pd
import numpy as np
import time
import sys
import os

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_deduplicator import DataDeduplicator, DeduplicationStrategy


class TestDataDeduplicator(unittest.TestCase):
    """DataDeduplicator测试类"""

    def setUp(self):
        """测试前准备"""
        self.deduplicator = DataDeduplicator()

        # 基础测试数据
        self.basic_df = pd.DataFrame({
            'id': [1, 2, 1, 3, 2, 4],
            'value': ['A', 'B', 'A', 'C', 'B', 'D'],
            'price': [10.0, 20.0, 10.0, 30.0, 20.0, 40.0]
        })

    def test_remove_duplicates_single_field_first_strategy(self):
        """测试单字段去重 - FIRST策略"""
        result = self.deduplicator.remove_duplicates(
            self.basic_df,
            key_columns=['id'],
            strategy=DeduplicationStrategy.FIRST
        )

        # 验证结果
        expected_ids = [1, 2, 3, 4]
        self.assertEqual(result['id'].tolist(), expected_ids)
        self.assertEqual(len(result), 4)

        # 验证保留的是第一次出现的记录
        first_row = result[result['id'] == 1].iloc[0]
        self.assertEqual(first_row['value'], 'A')

    def test_remove_duplicates_single_field_last_strategy(self):
        """测试单字段去重 - LAST策略"""
        result = self.deduplicator.remove_duplicates(
            self.basic_df,
            key_columns=['id'],
            strategy=DeduplicationStrategy.LAST
        )

        # 验证结果 - 去重后应该有4条记录
        self.assertEqual(len(result), 4)

        # 验证每个ID只出现一次
        unique_ids = result['id'].nunique()
        self.assertEqual(unique_ids, 4)

        # 验证保留的是最后一次出现的记录
        # 对于ID=2，最后一次出现的值应该是'B'
        id_2_rows = result[result['id'] == 2]
        self.assertEqual(len(id_2_rows), 1)
        self.assertEqual(id_2_rows.iloc[0]['value'], 'B')

    def test_remove_duplicates_multiple_fields(self):
        """测试多字段去重"""
        result = self.deduplicator.remove_duplicates(
            self.basic_df,
            key_columns=['id', 'value'],
            strategy=DeduplicationStrategy.FIRST
        )

        # 验证结果 - [1,A], [2,B], [3,C], [4,D] 应该保留
        self.assertEqual(len(result), 4)

        # 验证重复的 [1,A] 被正确去除
        duplicate_count = len(result[(result['id'] == 1) & (result['value'] == 'A')])
        self.assertEqual(duplicate_count, 1)

    def test_remove_duplicates_random_strategy(self):
        """测试随机策略去重"""
        # 设置随机种子以确保测试可重现
        np.random.seed(42)

        result = self.deduplicator.remove_duplicates(
            self.basic_df,
            key_columns=['id'],
            strategy=DeduplicationStrategy.RANDOM
        )

        # 验证去重结果
        unique_ids = result['id'].nunique()
        self.assertEqual(unique_ids, len(result))
        self.assertLessEqual(len(result), 4)

    def test_deduplicate_by_key_simple_function(self):
        """测试自定义函数去重 - 简单函数"""
        def composite_key(row):
            return f"{row['id']}_{row['value']}"

        result = self.deduplicator.deduplicate_by_key(
            self.basic_df,
            key_func=composite_key,
            strategy=DeduplicationStrategy.FIRST
        )

        # 验证结果
        self.assertEqual(len(result), 4)

        # 验证复合键的唯一性
        keys = [composite_key(row) for _, row in result.iterrows()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_deduplicate_by_key_complex_function(self):
        """测试自定义函数去重 - 复杂函数"""
        def complex_key(row):
            price_range = 'HIGH' if row['price'] > 15 else 'LOW'
            return f"{price_range}_{row['value'][0]}"

        result = self.deduplicator.deduplicate_by_key(
            self.basic_df,
            key_func=complex_key,
            strategy=DeduplicationStrategy.FIRST
        )

        # 验证结果
        self.assertLessEqual(len(result), len(self.basic_df))

        # 验证复合键的唯一性
        keys = [complex_key(row) for _, row in result.iterrows()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_get_duplicate_stats_basic(self):
        """测试基础统计信息"""
        stats = self.deduplicator.get_duplicate_stats(self.basic_df, ['id'])

        # 验证统计信息结构
        required_keys = [
            'total_records', 'unique_records', 'duplicate_groups',
            'duplicate_records', 'duplicate_rate', 'top_duplicates'
        ]
        for key in required_keys:
            self.assertIn(key, stats)

        # 验证统计信息准确性
        self.assertEqual(stats['total_records'], 6)
        self.assertEqual(stats['unique_records'], 4)
        self.assertEqual(stats['duplicate_records'], 2)
        self.assertAlmostEqual(stats['duplicate_rate'], 2/6, places=3)

    def test_get_duplicate_stats_multiple_fields(self):
        """测试多字段统计信息"""
        stats = self.deduplicator.get_duplicate_stats(self.basic_df, ['id', 'value'])

        # 验证多字段统计准确性
        self.assertEqual(stats['total_records'], 6)
        self.assertEqual(stats['unique_records'], 4)  # [1,A]重复一次

    def test_empty_dataframe(self):
        """测试空DataFrame"""
        empty_df = pd.DataFrame(columns=['id', 'value', 'price'])

        # 测试去重
        result = self.deduplicator.remove_duplicates(empty_df, ['id'])
        self.assertEqual(len(result), 0)

        # 测试统计
        stats = self.deduplicator.get_duplicate_stats(empty_df, ['id'])
        self.assertEqual(stats['total_records'], 0)
        self.assertEqual(stats['unique_records'], 0)

    def test_nonexistent_column(self):
        """测试不存在的列"""
        with self.assertRaises(ValueError):
            self.deduplicator.remove_duplicates(self.basic_df, ['nonexistent_column'])

    def test_invalid_key_columns_type(self):
        """测试无效的键列类型"""
        with self.assertRaises(ValueError):
            self.deduplicator.remove_duplicates(self.basic_df, key_columns=123)

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        # 生成大数据集
        n_records = 10000  # 使用较小的数据集进行单元测试

        large_df = pd.DataFrame({
            'id': np.random.randint(1, 1000, n_records),
            'value': np.random.choice(['A', 'B', 'C', 'D'], n_records),
            'price': np.random.uniform(10, 100, n_records)
        })

        # 测试单字段去重性能
        start_time = time.time()
        result = self.deduplicator.remove_duplicates(large_df, ['id'])
        elapsed_time = time.time() - start_time

        # 验证性能要求（10万条<3秒，这里1万条应该在0.3秒内）
        self.assertLess(elapsed_time, 0.3, f"单字段去重时间过长: {elapsed_time:.3f}秒")

        # 测试多字段去重性能
        start_time = time.time()
        result = self.deduplicator.remove_duplicates(large_df, ['id', 'value'])
        elapsed_time = time.time() - start_time

        # 验证性能要求
        self.assertLess(elapsed_time, 0.3, f"多字段去重时间过长: {elapsed_time:.3f}秒")

    def test_custom_function_performance(self):
        """测试自定义函数性能（较小数据集）"""
        # 生成中等数据集
        n_records = 1000

        test_df = pd.DataFrame({
            'time': [f'{i%24:02d}:{i%60:02d}:{i%60:02d}' for i in range(n_records)],
            'price': np.random.uniform(10, 100, n_records),
            'volume': np.random.randint(100, 10000, n_records),
            'stock_code': np.random.choice(['000001', '000002', '600519'], n_records)
        })

        def simple_key(row):
            return f"{row['time']}_{row['stock_code']}"

        # 测试自定义函数性能
        start_time = time.time()
        result = self.deduplicator.deduplicate_by_key(test_df, simple_key)
        elapsed_time = time.time() - start_time

        # 验证结果正确性
        self.assertLess(len(result), len(test_df))

        # 记录性能（自定义函数相对较慢，但应该在合理范围内）
        print(f"自定义函数去重 ({n_records:,} 条): {elapsed_time:.3f}秒")

    def test_accuracy_check(self):
        """测试准确率检查"""
        # 创建已知重复模式的数据
        test_df = pd.DataFrame({
            'group': ['A', 'A', 'B', 'B', 'C', 'A', 'B'],
            'value': [1, 1, 2, 2, 3, 1, 2]
        })

        # 测试单字段去重准确率
        result = self.deduplicator.remove_duplicates(test_df, ['group'])

        # 验证每个分组只保留一条记录
        for group in test_df['group'].unique():
            count_in_result = len(result[result['group'] == group])
            self.assertEqual(count_in_result, 1, f"分组 {group} 去重失败")

        # 测试多字段去重准确率
        result_multi = self.deduplicator.remove_duplicates(test_df, ['group', 'value'])

        # 验证组合的唯一性
        unique_combinations = test_df[['group', 'value']].drop_duplicates()
        self.assertEqual(len(result_multi), len(unique_combinations))

    def test_statistics_attributes(self):
        """测试统计属性"""
        result = self.deduplicator.remove_duplicates(
            self.basic_df,
            ['id'],
            keep_stats=True
        )

        # 验证统计属性存在
        self.assertTrue(hasattr(result, 'attrs'))
        self.assertIn('deduplication_stats', result.attrs)

        stats = result.attrs['deduplication_stats']
        self.assertIn('total_records', stats)
        self.assertIn('unique_records', stats)

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试全部重复的数据
        all_duplicate_df = pd.DataFrame({
            'id': [1, 1, 1, 1],
            'value': ['A', 'A', 'A', 'A']
        })

        result = self.deduplicator.remove_duplicates(all_duplicate_df, ['id'])
        self.assertEqual(len(result), 1)

        # 测试没有重复的数据
        no_duplicate_df = pd.DataFrame({
            'id': [1, 2, 3, 4],
            'value': ['A', 'B', 'C', 'D']
        })

        result = self.deduplicator.remove_duplicates(no_duplicate_df, ['id'])
        self.assertEqual(len(result), 4)

        # 测试包含NaN的数据
        nan_df = pd.DataFrame({
            'id': [1, 2, 1, np.nan],
            'value': ['A', 'B', 'A', 'C']
        })

        result = self.deduplicator.remove_duplicates(nan_df, ['id'])
        # NaN值在pandas中被认为是唯一的
        self.assertGreaterEqual(len(result), 2)

    def test_different_strategies_consistency(self):
        """测试不同策略的一致性"""
        # 使用确定性的数据
        test_df = pd.DataFrame({
            'key': ['A', 'A', 'B', 'B', 'C'],
            'value': [1, 2, 3, 4, 5]
        })

        # 测试FIRST策略
        first_result = self.deduplicator.remove_duplicates(
            test_df, ['key'], strategy=DeduplicationStrategy.FIRST
        )

        # 测试LAST策略
        last_result = self.deduplicator.remove_duplicates(
            test_df, ['key'], strategy=DeduplicationStrategy.LAST
        )

        # 验证结果长度相同
        self.assertEqual(len(first_result), len(last_result))

        # 验证键的唯一性
        self.assertEqual(len(first_result), first_result['key'].nunique())
        self.assertEqual(len(last_result), last_result['key'].nunique())


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
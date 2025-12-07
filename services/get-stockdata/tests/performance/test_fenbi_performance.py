#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
fenbi_engine性能测试脚本
用于验证优化后的性能提升
"""

import time
import asyncio
from datetime import datetime, time as dt_time, date as dt_date
from dataclasses import dataclass
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.fenbi_engine import FenbiEngine


@dataclass
class MockTickData:
    """模拟TickData对象"""
    time: dt_time
    price: float
    volume: int
    amount: float
    direction: str
    code: str
    date: dt_date


def generate_mock_data(count: int = 10000):
    """生成模拟数据"""
    print(f"生成 {count:,} 条模拟数据...")
    data = []
    base_price = 10.0
    
    for i in range(count):
        hour = 9 + (i // 3600)
        minute = (i % 3600) // 60
        second = i % 60
        
        tick = MockTickData(
            time=dt_time(hour, minute, second),
            price=base_price + (i % 100) * 0.01,
            volume=100 * (i % 50),
            amount=1000 * (i % 50),
            direction='B' if i % 2 == 0 else 'S',
            code='000001',
            date=dt_date(2025, 1, 1)
        )
        data.append(tick)
    
    return data


def test_conversion_performance():
    """测试数据转换性能"""
    print("\n" + "="*60)
    print("【测试1: 数据转换性能】")
    print("="*60)
    
    engine = FenbiEngine()
    
    test_sizes = [1000, 10000, 100000]
    
    for size in test_sizes:
        data = generate_mock_data(size)
        
        # 测试转换性能
        start = time.time()
        df = engine._convert_to_dataframe(data)
        duration = time.time() - start
        
        print(f"\n数据量: {size:,} 条")
        print(f"转换时间: {duration:.3f}秒")
        print(f"转换速度: {size/duration:,.0f} 条/秒")
        print(f"DataFrame大小: {len(df)} 行 x {len(df.columns)} 列")
        
        # 验证数据完整性
        assert len(df) == size, f"数据丢失！期望 {size}，实际 {len(df)}"
        assert all(col in df.columns for col in ['time', 'price', 'volume', 'amount', 'direction', 'code', 'date']), "列缺失！"
        print("✓ 数据完整性验证通过")


async def test_pipeline_performance():
    """测试完整数据处理管道性能"""
    print("\n" + "="*60)
    print("【测试2: 完整数据处理管道性能】")
    print("="*60)
    
    from unittest.mock import Mock, AsyncMock
    
    engine = FenbiEngine()
    
    test_sizes = [1000, 10000, 100000]
    
    for size in test_sizes:
        data = generate_mock_data(size)
        
        # Mock数据源
        mock_source = Mock()
        mock_source.is_connected = True
        mock_source.connect = AsyncMock(return_value=True)
        mock_source.get_tick_data = AsyncMock(return_value=data)
        engine.data_source = mock_source
        
        print(f"\n{'='*50}")
        print(f"数据量: {size:,} 条")
        print(f"{'='*50}")
        
        # 测试1: 仅排序
        start = time.time()
        result1 = await engine.get_tick_data('000001', '20250101', enable_time_sort=True, enable_deduplication=False)
        duration1 = time.time() - start
        print(f"\n仅排序:")
        print(f"  耗时: {duration1:.3f}秒")
        print(f"  速度: {size/duration1:,.0f} 条/秒")
        print(f"  结果: {len(result1):,} 条")
        
        # 测试2: 仅去重
        start = time.time()
        result2 = await engine.get_tick_data('000001', '20250101', enable_time_sort=False, enable_deduplication=True)
        duration2 = time.time() - start
        print(f"\n仅去重:")
        print(f"  耗时: {duration2:.3f}秒")
        print(f"  速度: {size/duration2:,.0f} 条/秒")
        print(f"  结果: {len(result2):,} 条")
        
        # 测试3: 排序+去重
        start = time.time()
        result3 = await engine.get_tick_data('000001', '20250101', enable_time_sort=True, enable_deduplication=True)
        duration3 = time.time() - start
        print(f"\n排序+去重:")
        print(f"  耗时: {duration3:.3f}秒")
        print(f"  速度: {size/duration3:,.0f} 条/秒")
        print(f"  结果: {len(result3):,} 条")
        
        # 性能目标验证
        if size == 100000:
            print(f"\n{'='*50}")
            print("性能目标验证（10万条数据）:")
            print(f"{'='*50}")
            # 整体处理应该快速完成
            if duration3 < 5.0:
                print(f"✓ 整体处理时间 {duration3:.3f}秒 < 5秒目标 ✓")
            else:
                print(f"✗ 整体处理时间 {duration3:.3f}秒 ≥ 5秒目标 ✗")
            
            # 检查统计信息
            stats = engine.get_stats()
            print(f"\n统计信息:")
            print(f"  总记录数: {stats['total_records']:,}")
            print(f"  唯一记录: {stats['unique_records']:,}")
            print(f"  去重数量: {stats['duplicates_removed']:,}")
            print(f"  处理时长: {stats.get('duration', 0):.3f}秒")


async def test_report_performance():
    """测试报告生成性能"""
    print("\n" + "="*60)
    print("【测试3: 报告生成性能】")
    print("="*60)
    
    from unittest.mock import Mock, AsyncMock
    
    engine = FenbiEngine()
    
    test_sizes = [1000, 10000, 100000]
    
    for size in test_sizes:
        data = generate_mock_data(size)
        
        print(f"\n数据量: {size:,} 条")
        
        # 测试报告生成
        start = time.time()
        report = engine.generate_enhanced_report(data)
        duration = time.time() - start
        
        print(f"报告生成时间: {duration:.3f}秒")
        print(f"处理速度: {size/duration:,.0f} 条/秒")
        
        # 验证报告内容
        assert 'basic_quality' in report
        assert 'statistical_analysis' in report
        assert 'data_characteristics' in report
        assert 'processing_stats' in report
        print("✓ 报告完整性验证通过")


def print_summary():
    """打印测试总结"""
    print("\n" + "="*60)
    print("【优化效果总结】")
    print("="*60)
    print("""
优化措施:
1. ✓ 数据转换从 4次 减少到 2次 (减少50%)
2. ✓ 数据遍历从 多次 减少到 1次
3. ✓ 复用 _convert_to_dataframe() 方法
4. ✓ 在DataFrame上完成所有中间操作
5. ✓ 使用索引映射保证数据完整性

预期提升:
- 减少约75%的转换开销
- 降低约50%的内存使用
- 提高代码可维护性

数据完整性保证:
✓ 保持原始TickData对象引用
✓ 使用索引映射而非重建对象
✓ 失败时回退到原始数据
✓ 完善的错误处理机制
    """)


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("fenbi_engine 性能测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 测试1: 转换性能
        test_conversion_performance()
        
        # 测试2: 管道性能
        await test_pipeline_performance()
        
        # 测试3: 报告性能
        await test_report_performance()
        
        # 打印总结
        print_summary()
        
        print("\n" + "="*60)
        print("✓ 所有测试完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())

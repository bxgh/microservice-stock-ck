#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuotesService 性能基准测试

测试场景:
1. 批量查询性能 (1000只股票)
2. 缓存性能
3. 并发请求性能
4. 内存使用

目标:
- 1000只股票 < 3秒
- 缓存命中率 > 80%
- 支持 10个并发请求

Usage:
    python scripts/benchmark_quotes_service.py
    
@author: EPIC-007 Story 007.02b
@date: 2025-12-06
"""

import asyncio
import time
import sys
import os
from typing import List

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data_services import QuotesService


def generate_stock_codes(count: int) -> List[str]:
    """生成测试用股票代码
    
    Args:
        count: 数量
        
    Returns:
        List[str]: 股票代码列表
    """
    codes = []
    
    # 深圳股票 000001-003000
    for i in range(1, min(count // 2 + 1, 3001)):
        codes.append(f"{i:06d}")
        if len(codes) >= count:
            break
    
    # 上海股票 600000-603000
    for i in range(600000, min(600000 + count, 603001)):
        codes.append(f"{i:06d}")
        if len(codes) >= count:
            break
    
    return codes[:count]


async def benchmark_batch_query(service: QuotesService, batch_size: int = 1000):
    """测试批量查询性能
    
    Args:
        service: QuotesService 实例
        batch_size: 批量大小
    """
    print(f"\n{'='*60}")
    print(f"📊 批量查询性能测试 ({batch_size} 只股票)")
    print(f"{'='*60}")
    
    codes = generate_stock_codes(batch_size)
    
    # 第一次查询（无缓存）
    print(f"\n🔄 第一次查询 (无缓存)...")
    start = time.time()
    try:
        df = await service.get_quotes(codes)
        elapsed = time.time() - start
        
        print(f"✅ 成功获取 {len(df)} 只股票")
        print(f"⏱️  耗时: {elapsed:.2f}s")
        print(f"📈 平均速度: {len(df) / elapsed:.0f} 只/秒")
        
        if elapsed < 3.0:
            print(f"✅ 性能达标 (< 3秒)")
        else:
            print(f"⚠️  性能未达标 (目标 < 3秒, 实际 {elapsed:.2f}s)")
    
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return
    
    # 第二次查询（有缓存）
    print(f"\n🔄 第二次查询 (有缓存)...")
    start = time.time()
    try:
        df = await service.get_quotes(codes)
        elapsed = time.time() - start
        
        print(f"✅ 成功获取 {len(df)} 只股票")
        print(f"⏱️  耗时: {elapsed:.2f}s")
        print(f"📈 平均速度: {len(df) / elapsed:.0f} 只/秒")
        
        if elapsed < 0.5:
            print(f"✅ 缓存性能优秀 (< 0.5秒)")
        else:
            print(f"⚠️  缓存性能一般 ({elapsed:.2f}s)")
    
    except Exception as e:
        print(f"❌ 查询失败: {e}")


async def benchmark_cache_hit_rate(service: QuotesService):
    """测试缓存命中率
    
    Args:
        service: QuotesService 实例
    """
    print(f"\n{'='*60}")
    print(f"💾 缓存命中率测试")
    print(f"{'='*60}")
    
    codes = generate_stock_codes(100)
    
    # 清理缓存
    await service.clear_cache()
    
    # 查询10次
    print(f"\n🔄 连续查询 10 次...")
    for i in range(10):
        await service.get_quotes(codes)
        await asyncio.sleep(0.1)
    
    # 获取统计
    stats = service.get_stats()
    print(f"\n📊 统计结果:")
    print(f"   总请求: {stats['total_requests']}")
    print(f"   缓存命中: {stats['cache_hits']}")
    print(f"   缓存未命中: {stats['cache_misses']}")
    print(f"   缓存命中率: {stats['cache_hit_rate']}")
    
    # 解析命中率
    hit_rate_str = stats['cache_hit_rate']
    if hit_rate_str != "N/A":
        hit_rate = float(hit_rate_str.rstrip('%'))
        if hit_rate >= 80:
            print(f"✅ 缓存命中率达标 (>= 80%)")
        else:
            print(f"⚠️  缓存命中率未达标 (目标 >= 80%, 实际 {hit_rate:.1f}%)")


async def benchmark_concurrent_requests(service: QuotesService, concurrency: int = 10):
    """测试并发请求性能
    
    Args:
        service: QuotesService 实例
        concurrency: 并发数
    """
    print(f"\n{'='*60}")
    print(f"🚀 并发请求测试 ({concurrency} 个并发)")
    print(f"{'='*60}")
    
    codes = generate_stock_codes(100)
    
    print(f"\n🔄 发起 {concurrency} 个并发请求...")
    start = time.time()
    
    # 创建并发任务
    tasks = [service.get_quotes(codes) for _ in range(concurrency)]
    
    try:
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        success_count = sum(1 for df in results if not df.empty)
        
        print(f"✅ {success_count}/{concurrency} 个请求成功")
        print(f"⏱️  总耗时: {elapsed:.2f}s")
        print(f"📈 平均每请求: {elapsed / concurrency:.2f}s")
        
        if success_count == concurrency:
            print(f"✅ 并发安全性验证通过")
        else:
            print(f"⚠️  部分请求失败")
    
    except Exception as e:
        print(f"❌ 并发测试失败: {e}")


async def benchmark_small_batches(service: QuotesService):
    """测试小批量查询性能
    
    Args:
        service: QuotesService 实例
    """
    print(f"\n{'='*60}")
    print(f"📦 小批量查询性能测试")
    print(f"{'='*60}")
    
    batch_sizes = [1, 10, 50, 100]
    
    for size in batch_sizes:
        codes = generate_stock_codes(size)
        
        start = time.time()
        df = await service.get_quotes(codes)
        elapsed = time.time() - start
        
        print(f"\n{size:3d} 只股票: {elapsed*1000:6.1f}ms  "
              f"({len(df)/elapsed:6.0f} 只/秒)")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("QuotesService 性能基准测试")
    print("=" * 60)
    
    service = QuotesService()
    
    # 初始化
    print("\n🔌 初始化服务...")
    if not await service.initialize():
        print("❌ 初始化失败")
        return
    print("✅ 初始化成功")
    
    try:
        # 1. 批量查询性能
        await benchmark_batch_query(service, batch_size=1000)
        
        # 2. 缓存命中率
        await benchmark_cache_hit_rate(service)
        
        # 3. 并发请求
        await benchmark_concurrent_requests(service, concurrency=10)
        
        # 4. 小批量查询
        await benchmark_small_batches(service)
        
        # 最终统计
        print(f"\n{'='*60}")
        print(f"📊 最终统计")
        print(f"={'='*60}")
        stats = service.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print(f"\n{'='*60}")
        print(f"✅ 性能测试完成")
        print(f"{'='*60}")
    
    finally:
        await service.close()
        print("\n🔌 服务已关闭")


if __name__ == "__main__":
    asyncio.run(main())

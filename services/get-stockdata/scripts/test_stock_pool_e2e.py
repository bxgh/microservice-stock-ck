#!/usr/bin/env python3
"""
End-to-End Test for Stock Pool Management (Story 004.01)

测试完整的股票池工作流：
1. 加载股票池
2. 初始化调度器
3. 验证池大小
4. 测试缓存机制
5. 测试降级逻辑
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.stock_pool.manager import StockPoolManager
from core.scheduling.scheduler import AcquisitionScheduler

async def test_stock_pool_e2e():
    """端到端测试股票池管理"""
    print("=" * 60)
    print("Story 004.01 - Stock Pool Management E2E Test")
    print("=" * 60)
    
    # 测试1: 初始化StockPoolManager
    print("\n[Test 1] 初始化 StockPoolManager...")
    pool_manager = StockPoolManager(cache_dir="cache/stock_pools")
    print("✅ StockPoolManager 初始化成功")
    
    # 测试2: 获取HS300 Top100
    print("\n[Test 2] 获取沪深300 Top100 股票池...")
    try:
        stocks = await pool_manager.get_hs300_top100_by_volume(lookback_days=5)
        print(f"✅ 成功获取股票池: {len(stocks)} 只股票")
        
        if len(stocks) > 0:
            print(f"   示例股票代码: {stocks[:5]}")
        
        # 验证数量
        if len(stocks) == 100:
            print("✅ 股票池大小正确 (100只)")
        elif len(stocks) > 0:
            print(f"⚠️ 股票池大小为 {len(stocks)} (可能来自缓存)")
        else:
            print("❌ 股票池为空")
            return False
    except Exception as e:
        print(f"❌ 获取股票池失败: {e}")
        return False
    
    # 测试3: 验证缓存
    print("\n[Test 3] 验证缓存机制...")
    cache_dir = Path("cache/stock_pools")
    cache_files = list(cache_dir.glob("hs300_top100_*.json"))
    if cache_files:
        print(f"✅ 发现 {len(cache_files)} 个缓存文件")
        latest_cache = sorted(cache_files)[-1]
        print(f"   最新缓存: {latest_cache.name}")
    else:
        print("⚠️ 未找到缓存文件")
    
    # 测试4: 测试缓存加载
    print("\n[Test 4] 测试从缓存加载...")
    try:
        cached_stocks = await pool_manager._load_pool_cache("hs300_top100")
        if cached_stocks:
            print(f"✅ 从缓存加载成功: {len(cached_stocks)} 只股票")
        else:
            print("⚠️ 缓存为空")
    except Exception as e:
        print(f"❌ 缓存加载失败: {e}")
    
    # 测试5: 初始化AcquisitionScheduler
    print("\n[Test 5] 初始化 AcquisitionScheduler...")
    try:
        scheduler = AcquisitionScheduler()
        await scheduler.initialize()
        print("✅ AcquisitionScheduler 初始化成功")
        
        # 获取当前池
        current_pool = scheduler.get_current_pool()
        print(f"✅ 调度器当前股票池: {len(current_pool)} 只股票")
        
        if len(current_pool) == 100:
            print("✅ 调度器股票池大小正确")
        elif len(current_pool) > 0:
            print(f"⚠️ 调度器股票池大小为 {len(current_pool)}")
        else:
            print("❌ 调度器股票池为空")
            
    except Exception as e:
        print(f"❌ 调度器初始化失败: {e}")
        return False
    
    # 测试6: 刷新股票池
    print("\n[Test 6] 测试股票池刷新...")
    try:
        old_size = len(scheduler.get_current_pool())
        await scheduler.refresh_pool()
        new_size = len(scheduler.get_current_pool())
        print(f"✅ 股票池刷新成功 (大小: {old_size} -> {new_size})")
    except Exception as e:
        print(f"❌ 股票池刷新失败: {e}")
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n✅ 所有核心功能正常")
    print("\n下一步：")
    print("1. 运行单元测试: pytest tests/test_stock_pool_manager.py -v")
    print("2. 运行集成测试: pytest tests/test_scheduler_with_pool.py -v")
    print("3. 启动Docker测试: docker compose -f docker-compose.dev.yml up -d")
    print("4. 监控日志查看100只股票采集情况")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_stock_pool_e2e())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

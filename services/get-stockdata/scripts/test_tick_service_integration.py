#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TickService 真实环境集成测试

测试分笔成交服务在真实数据源环境下的功能。

@author: EPIC-007 Story 007.02b
@date: 2025-12-07
"""

import asyncio
import time
from datetime import datetime, timedelta

# 使用 src 路径导入
import sys
sys.path.insert(0, '/app')

from src.data_services import TickService


async def test_tick_service_integration():
    """测试 TickService 真实环境集成"""
    
    print("=" * 60)
    print("TickService 真实环境集成测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    service = TickService()
    
    try:
        # 1. 初始化
        print("1️⃣ 初始化服务...")
        start = time.time()
        success = await service.initialize()
        init_time = time.time() - start
        print(f"   初始化: {'✅ 成功' if success else '❌ 失败'} ({init_time:.2f}s)")
        
        if not success:
            print("   ⛔ 初始化失败，退出测试")
            return False
        
        # 2. 获取历史分笔数据 (昨天或最近交易日)
        # 使用历史日期确保有数据
        test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        test_code = '000001'  # 平安银行
        
        print(f"\n2️⃣ 获取历史分笔数据 ({test_code} @ {test_date})...")
        start = time.time()
        try:
            ticks = await service.get_tick(test_code, test_date)
            tick_time = time.time() - start
            
            if not ticks.empty:
                print(f"   获取分笔: ✅ {len(ticks)} 笔 ({tick_time:.2f}s)")
                print(f"   字段: {list(ticks.columns)}")
                print(f"   时间范围: {ticks['time'].min()} - {ticks['time'].max()}")
                print(f"   价格范围: {ticks['price'].min():.2f} - {ticks['price'].max():.2f}")
                
                # 显示前5笔
                print(f"\n   前5笔分笔:")
                print(ticks[['time', 'price', 'volume', 'amount', 'direction']].head().to_string(index=False))
            else:
                print(f"   获取分笔: ⚠️ 无数据 ({tick_time:.2f}s)")
                print(f"   可能原因: {test_date} 不是交易日，或 mootdx 非交易时段无数据")
                
        except Exception as e:
            print(f"   获取分笔: ❌ 失败 - {e}")
            ticks = None
        
        # 3. 获取统计摘要
        print(f"\n3️⃣ 获取统计摘要...")
        try:
            summary = await service.get_tick_summary(test_code, test_date)
            print(f"   摘要: ✅ 成功")
            print(f"   总成交量: {summary.get('total_volume', 0):,} 手")
            print(f"   总成交额: {summary.get('total_amount', 0):,.0f} 元")
            print(f"   分笔笔数: {summary.get('tick_count', 0)} 笔")
            print(f"   净流入: {summary.get('net_inflow', 0):,.0f} 元")
        except Exception as e:
            print(f"   摘要: ❌ 失败 - {e}")
        
        # 4. 大单筛选
        print(f"\n4️⃣ 大单筛选 (阈值: 50万)...")
        try:
            large_orders = await service.get_large_orders(test_code, test_date, threshold=500_000)
            print(f"   大单: ✅ {len(large_orders)} 笔")
            if not large_orders.empty:
                print(f"\n   大单列表 (前10笔):")
                display_cols = ['time', 'price', 'amount', 'direction', 'order_level']
                display_cols = [c for c in display_cols if c in large_orders.columns]
                print(large_orders[display_cols].head(10).to_string(index=False))
        except Exception as e:
            print(f"   大单: ❌ 失败 - {e}")
        
        # 5. 资金流向分析
        print(f"\n5️⃣ 资金流向分析...")
        try:
            flow = await service.analyze_capital_flow(test_code, test_date)
            print(f"   分析: ✅ 成功")
            print(f"   总买入: {flow.total_buy_amount:,.0f} 元")
            print(f"   总卖出: {flow.total_sell_amount:,.0f} 元")
            print(f"   净流入: {flow.net_inflow:,.0f} 元")
            print(f"   流向: {'📈 流入' if flow.is_inflow else '📉 流出'}")
            print(f"   强度: {flow.inflow_strength}")
            print(f"   大单数: {flow.large_order_count} 笔")
            print(f"   买卖比: {flow.buy_sell_ratio:.2f}")
            
            # 分时段分析
            if flow.time_analysis:
                print(f"\n   分时段分析:")
                for period, stats in flow.time_analysis.items():
                    net = stats.get('net_inflow', 0)
                    direction = '📈' if net > 0 else '📉' if net < 0 else '➖'
                    print(f"   {period}: {direction} {net:,.0f} 元 ({stats.get('tick_count', 0)} 笔)")
                    
        except Exception as e:
            print(f"   分析: ❌ 失败 - {e}")
        
        # 6. 统计信息
        print(f"\n6️⃣ 服务统计...")
        stats = service.get_stats()
        print(f"   总请求数: {stats.get('total_requests', 0)}")
        print(f"   缓存命中率: {stats.get('cache_hit_rate', 'N/A')}")
        print(f"   Provider调用: {stats.get('provider_calls', 0)}")
        
        print("\n" + "=" * 60)
        print("✅ 集成测试完成")
        print("=" * 60)
        return True
        
    finally:
        await service.close()


if __name__ == '__main__':
    asyncio.run(test_tick_service_integration())

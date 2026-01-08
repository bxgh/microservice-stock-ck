#!/usr/bin/env python3
"""
测试 get_all_stocks() 方法
"""
import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, '/home/bxgh/microservice-stock/services/gsd-worker/src')

from core.tick_sync_service import TickSyncService

async def test_get_all_stocks():
    service = TickSyncService()
    await service.initialize()
    
    try:
        print("正在调用 get_all_stocks()...")
        all_stocks = await service.get_all_stocks()
        
        print(f"\n✅ 获取到 {len(all_stocks)} 只股票")
        print(f"\n前20只: {all_stocks[:20]}")
        print(f"后20只: {all_stocks[-20:]}")
        
        # 统计各板块
        sz_main = [s for s in all_stocks if s.startswith('00')]
        sz_gem = [s for s in all_stocks if s.startswith('30')]
        sh_main = [s for s in all_stocks if s.startswith('60')]
        sh_star = [s for s in all_stocks if s.startswith('68')]
        
        print(f"\n板块分布:")
        print(f"  深市主板 (00xxxx): {len(sz_main)}")
        print(f"  创业板 (30xxxx): {len(sz_gem)}")
        print(f"  沪市主板 (60xxxx): {len(sh_main)}")
        print(f"  科创板 (68xxxx): {len(sh_star)}")
        
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(test_get_all_stocks())

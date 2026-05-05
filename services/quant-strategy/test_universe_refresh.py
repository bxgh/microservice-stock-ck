#!/usr/bin/env python3
"""测试 universe_pool_service.refresh_universe_pool()"""
import sys
sys.path.insert(0, '/home/bxgh/microservice-stock/services/quant-strategy/src')

import asyncio
import logging
logging.basicConfig(level=logging.INFO)

from services.stock_pool.universe_pool_service import universe_pool_service
from database import init_database

async def test():
    # 初始化数据库
    await init_database()
    
    # 初始化服务
    await universe_pool_service.initialize()
    
    # 刷新
    print("触发 refresh_universe_pool...")
    result = await universe_pool_service.refresh_universe_pool()
    
    print(f"\n结果:")
    print(f"  成功: {result.success}")
    print(f"  总股票数: {result.total_stocks}")
    print(f"  合格数: {result.qualified_count}")
    print(f"  新增: {result.new_entries}")
    print(f"  消息: {result.message}")

if __name__ == "__main__":
    asyncio.run(test())

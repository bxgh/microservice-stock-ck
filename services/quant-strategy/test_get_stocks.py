#!/usr/bin/env python3
"""测试 stock_data_provider.get_all_stocks()"""
import sys
sys.path.insert(0, '/home/bxgh/microservice-stock/services/quant-strategy/src')

import asyncio
from adapters.stock_data_provider import data_provider

async def test():
    await data_provider.initialize()
    stocks = await data_provider.get_all_stocks(limit=5)
    print(f"返回数量: {len(stocks)}")
    if stocks:
        print(f"第一条记录: {stocks[0]}")
    else:
        print("❌ 返回为空")

if __name__ == "__main__":
    asyncio.run(test())

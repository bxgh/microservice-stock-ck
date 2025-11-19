#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票客户端集成测试脚本
"""

import asyncio
import sys
import os

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.stock_code_client import stock_client_instance

async def test_stock_client():
    print('=== 测试股票客户端初始化 ===')
    try:
        await stock_client_instance.initialize()
        print('✅ 股票客户端初始化成功')
    except Exception as e:
        print(f'❌ 股票客户端初始化失败: {e}')
        return

    print('\n=== 测试获取全市场股票列表 ===')
    try:
        stocks = await stock_client_instance.get_all_stocks(10)
        print(f'✅ 成功获取 {len(stocks)} 只股票数据')
        if stocks:
            sample = stocks[0]
            print(f'   示例股票: {sample.stock_code} - {sample.stock_name} ({sample.exchange})')
            print(f'   代码映射: Tushare={sample.code_mappings.tushare}, AKShare={sample.code_mappings.akshare}')
    except Exception as e:
        print(f'❌ 获取股票列表失败: {e}')
        return

    print('\n=== 测试按交易所获取股票 ===')
    try:
        sh_stocks = await stock_client_instance.get_stocks_by_exchange('SH')
        print(f'✅ 成功获取上海证券交易所 {len(sh_stocks)} 只股票')

        sz_stocks = await stock_client_instance.get_stocks_by_exchange('SZ')
        print(f'✅ 成功获取深圳证券交易所 {len(sz_stocks)} 只股票')
    except Exception as e:
        print(f'❌ 按交易所获取股票失败: {e}')

    print('\n=== 测试股票搜索功能 ===')
    try:
        search_results = await stock_client_instance.search_stocks('平安', 5)
        print(f'✅ 搜索 "平安" 找到 {len(search_results)} 个结果')
        for stock in search_results:
            print(f'   - {stock.stock_code} - {stock.stock_name} ({stock.exchange})')
    except Exception as e:
        print(f'❌ 股票搜索失败: {e}')

    print('\n=== 测试获取股票详情 ===')
    try:
        if stocks:
            detail = await stock_client_instance.get_stock_detail(stocks[0].stock_code)
            if detail:
                print(f'✅ 成功获取股票详情: {detail.stock_code} - {detail.stock_name}')
                print(f'   上市日期: {detail.list_date}')
                print(f'   数据来源: {detail.data_source}')
            else:
                print('❌ 未找到股票详情')
    except Exception as e:
        print(f'❌ 获取股票详情失败: {e}')

    print('\n=== 测试缓存状态 ===')
    try:
        cache_status = await stock_client_instance.get_cache_status()
        print('✅ 缓存状态获取成功:')
        print(f'   内存缓存键数量: {cache_status["memory_cache"]["keys_count"]}')
        print(f'   Redis缓存启用: {cache_status["redis_cache"]["enabled"]}')
    except Exception as e:
        print(f'❌ 获取缓存状态失败: {e}')

    print('\n=== 测试完成 ===')
    await stock_client_instance.close()

if __name__ == "__main__":
    asyncio.run(test_stock_client())
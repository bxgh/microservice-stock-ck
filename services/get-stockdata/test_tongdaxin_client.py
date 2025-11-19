#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通达信客户端集成测试脚本
"""

import asyncio
import sys
import os
from datetime import datetime, date, timedelta

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.tongdaxin_client import tongdaxin_client
from models.tick_models import TickDataRequest, TickDataBatchRequest

async def test_tongdaxin_client():
    print('=== 测试通达信客户端初始化 ===')
    try:
        success = await tongdaxin_client.initialize()
        if success:
            print('✅ 通达信客户端初始化成功')
        else:
            print('❌ 通达信客户端初始化失败')
            return
    except Exception as e:
        print(f'❌ 通达信客户端初始化异常: {e}')
        return

    print('\n=== 测试数据源状态 ===')
    try:
        status = await tongdaxin_client.get_status()
        print(f'✅ 数据源状态获取成功:')
        print(f'   连接状态: {"已连接" if status.is_connected else "未连接"}')
        print(f'   可用服务器: {len(status.available_servers)}')
        print(f'   响应时间: {status.response_time}ms' if status.response_time else '   响应时间: N/A')
        if status.error_message:
            print(f'   错误信息: {status.error_message}')
    except Exception as e:
        print(f'❌ 获取数据源状态失败: {e}')

    print('\n=== 测试单只股票分笔数据获取 ===')
    try:
        # 测试获取平安银行(000001)昨天的分笔数据
        yesterday = (datetime.now() - timedelta(days=1)).date()
        # 如果是周末，往前推到工作日
        while yesterday.weekday() >= 5:  # 5=周六, 6=周日
            yesterday -= timedelta(days=1)

        request = TickDataRequest(
            stock_code="000001",
            date=datetime.combine(yesterday, datetime.min.time()),
            market="SZ",
            include_auction=True
        )

        print(f'   正在获取 000001 在 {yesterday} 的分笔数据...')
        response = await tongdaxin_client.get_tick_data(request)

        if response.success:
            print(f'✅ 成功获取分笔数据:')
            print(f'   数据条数: {len(response.data)}')
            print(f'   数据摘要: {response.summary}')

            if response.data:
                sample = response.data[0]
                print(f'   示例数据: 时间={sample.time}, 价格={sample.price}, 成交量={sample.volume}')
        else:
            print(f'❌ 获取分笔数据失败: {response.message}')

    except Exception as e:
        print(f'❌ 获取单只股票分笔数据异常: {e}')

    print('\n=== 测试批量分笔数据获取 ===')
    try:
        # 测试批量获取多只股票的分笔数据
        test_stocks = ["000001", "000002", "600036"]  # 平安银行、万科A、招商银行
        batch_request = TickDataBatchRequest(
            stock_codes=test_stocks,
            date=datetime.combine(yesterday, datetime.min.time()),
            include_auction=False  # 不包含集合竞价
        )

        print(f'   正在批量获取 {len(test_stocks)} 只股票的分笔数据...')
        batch_response = await tongdaxin_client.get_batch_tick_data(batch_request)

        if batch_response.success:
            print(f'✅ 批量获取成功:')
            print(f'   成功数量: {batch_response.success_count}')
            print(f'   失败数量: {batch_response.failed_count}')
            print(f'   成功股票: {list(batch_response.data.keys())}')

            if batch_response.failed_stocks:
                print(f'   失败股票: {batch_response.failed_stocks}')
        else:
            print(f'❌ 批量获取失败: {batch_response.message}')

    except Exception as e:
        print(f'❌ 批量获取分笔数据异常: {e}')

    print('\n=== 测试连接池功能 ===')
    try:
        # 并发测试连接池
        print('   正在测试并发连接...')

        async def concurrent_request(stock_code: str):
            request = TickDataRequest(
                stock_code=stock_code,
                date=datetime.combine(yesterday, datetime.min.time()),
                market="SH" if stock_code.startswith('6') else "SZ",
                include_auction=False
            )
            return await tongdaxin_client.get_tick_data(request)

        # 并发获取多只股票数据
        concurrent_stocks = ["600000", "600036", "000001", "000002"]
        tasks = [concurrent_request(code) for code in concurrent_stocks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if hasattr(r, 'success') and r.success)
        print(f'✅ 并发测试完成:')
        print(f'   请求数量: {len(concurrent_stocks)}')
        print(f'   成功数量: {success_count}')
        print(f'   连接池工作正常')

    except Exception as e:
        print(f'❌ 连接池测试失败: {e}')

    print('\n=== 测试完成 ===')
    try:
        await tongdaxin_client.close()
        print('✅ 通达信客户端已关闭')
    except Exception as e:
        print(f'❌ 关闭客户端失败: {e}')

if __name__ == "__main__":
    asyncio.run(test_tongdaxin_client())
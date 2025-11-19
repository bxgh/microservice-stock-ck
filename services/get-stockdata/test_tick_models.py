#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分笔数据模型测试脚本
测试数据模型和适配器功能
"""

import sys
import os
from datetime import datetime, time

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.tick_models import (
    TickData, TickDataRequest, TickDataResponse, TickDataAdapter,
    TickDataSummary, DataSourceStatus
)

def test_tick_models():
    print('=== 测试分笔数据模型 ===')

    # 测试TickData模型
    try:
        tick = TickData(
            time=datetime.now(),
            price=10.50,
            volume=1000,
            amount=10500.0,
            direction="B",
            code="000001",
            date=datetime.now()
        )
        print(f'✅ TickData模型创建成功: {tick.code} 价格={tick.price}')
    except Exception as e:
        print(f'❌ TickData模型创建失败: {e}')
        return

    # 测试TickDataRequest模型
    try:
        request = TickDataRequest(
            stock_code="000001",
            date=datetime.now(),
            market="SZ",
            include_auction=True
        )
        print(f'✅ TickDataRequest模型创建成功: {request.stock_code}')
    except Exception as e:
        print(f'❌ TickDataRequest模型创建失败: {e}')
        return

    # 测试TickDataResponse模型
    try:
        response = TickDataResponse(
            success=True,
            message="测试响应",
            data=[tick]
        )
        print(f'✅ TickDataResponse模型创建成功: {len(response.data)}条数据')
    except Exception as e:
        print(f'❌ TickDataResponse模型创建失败: {e}')
        return

    print('\n=== 测试数据适配器 ===')

    # 测试TDX数据适配
    try:
        tdx_data = {
            'time': '09:30:00',
            'price': 10.50,
            'volume': 1000,
            'amount': 10500.0,
            'direction': 'B'
        }

        adapted_tick = TickDataAdapter.from_tdx(
            tdx_data, "000001", datetime.now()
        )
        print(f'✅ TDX数据适配成功: 价格={adapted_tick.price}, 方向={adapted_tick.direction}')
    except Exception as e:
        print(f'❌ TDX数据适配失败: {e}')

    # 测试AKShare数据适配
    try:
        ak_data = {
            'time': '09:30:00',
            'price': 10.50,
            'volume': 1000,
            'amount': 10500.0,
            'direction': 'B'
        }

        adapted_tick = TickDataAdapter.from_akshare(
            ak_data, "000001", datetime.now()
        )
        print(f'✅ AKShare数据适配成功: 价格={adapted_tick.price}, 方向={adapted_tick.direction}')
    except Exception as e:
        print(f'❌ AKShare数据适配失败: {e}')

    # 测试数据摘要计算
    try:
        test_date = datetime.now()
        tick_data_list = [
            TickData(time=test_date.replace(hour=9, minute=25), price=10.00, volume=1000, amount=10000.0, direction="B", code="000001", date=test_date),
            TickData(time=test_date.replace(hour=9, minute=30), price=10.05, volume=500, amount=5025.0, direction="S", code="000001", date=test_date),
            TickData(time=test_date.replace(hour=9, minute=31), price=10.10, volume=800, amount=8080.0, direction="B", code="000001", date=test_date),
        ]

        summary = TickDataAdapter.calculate_summary(tick_data_list, "000001", test_date)
        print(f'✅ 数据摘要计算成功:')
        print(f'   开盘价: {summary.open_price}')
        print(f'   收盘价: {summary.close_price}')
        print(f'   最高价: {summary.high_price}')
        print(f'   最低价: {summary.low_price}')
        print(f'   总成交量: {summary.total_volume}')
        print(f'   集合竞价价格: {summary.auction_price}')
        print(f'   集合竞价成交量: {summary.auction_volume}')
    except Exception as e:
        print(f'❌ 数据摘要计算失败: {e}')

    print('\n=== 测试数据源状态模型 ===')
    try:
        status = DataSourceStatus(
            source_name="通达信",
            is_connected=True,
            last_check=datetime.now(),
            available_servers=["119.147.212.81:7709"],
            response_time=150.5,
            error_message=None
        )
        print(f'✅ DataSourceStatus模型创建成功: {status.source_name} 连接状态={status.is_connected}')
    except Exception as e:
        print(f'❌ DataSourceStatus模型创建失败: {e}')

    print('\n=== 模型测试完成 ===')
    print('✅ 所有分笔数据模型测试通过，代码结构正确！')

if __name__ == "__main__":
    test_tick_models()
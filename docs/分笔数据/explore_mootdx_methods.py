#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
探索mootdx库支持的所有数据获取方法
"""

from mootdx.quotes import Quotes

# 创建客户端
client = Quotes.factory(market='std')

# 打印客户端的所有方法
print("=== mootdx Quotes客户端支持的方法 ===")
methods = [method for method in dir(client) if not method.startswith('_')]
for method in sorted(methods):
    print(f"- {method}")

print("\n=== 测试分笔数据相关方法 ===")

# 测试可能的分笔数据方法
test_methods = [
    'transactions',  # 分笔成交
    'ticks',         # 分笔数据
    'transaction',   # 单笔成交
    'tick',          # 单笔数据
    'minute',        # 分钟数据
    'minutes',       # 分钟数据（复数）
    'bars',          # K线数据
    'index_bars',    # 指数K线
    'stock_bars',    # 股票K线
]

for method in test_methods:
    if hasattr(client, method):
        print(f"支持方法: {method}")
        # 尝试获取方法签名
        try:
            func = getattr(client, method)
            print(f"  函数: {func}")
        except Exception as e:
            print(f"  获取函数信息失败: {e}")
    else:
        print(f"不支持方法: {method}")

print("\n=== 测试获取分笔数据 ===")

# 尝试获取分笔数据
try:
    # 测试获取分笔成交数据
    print("尝试获取分笔成交数据...")
    # 根据mootdx文档，分笔数据可能是transactions方法
    tick_data = client.transactions(symbol='000001', date='20241028', start=0, offset=10)
    print(f"分笔数据获取成功: {type(tick_data)}")
    if hasattr(tick_data, 'head'):
        print(f"数据前几行:\n{tick_data.head()}")
    elif hasattr(tick_data, '__len__'):
        print(f"数据长度: {len(tick_data)}")
        if len(tick_data) > 0:
            print(f"第一条数据: {tick_data[0]}")
except Exception as e:
    print(f"获取分笔数据失败: {e}")

# 关闭连接
client.close()
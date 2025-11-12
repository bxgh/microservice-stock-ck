#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分笔数据获取简单示例
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tick_data_fetcher import TickDataFetcher


def simple_example():
    """简单示例：获取单个股票的分笔数据"""

    # 创建获取器
    fetcher = TickDataFetcher()

    try:
        # 获取平安银行的分笔数据
        print("获取平安银行(000001)的分笔数据...")
        data = fetcher.get_transactions_data(
            symbol='000001',
            date='20241028',
            offset=20
        )

        # 显示数据
        if not data.empty:
            print(f"\n获取到 {len(data)} 条记录:")
            print(data[['time', 'price', 'vol', 'buyorsell']].head(10))

            # 简单统计
            print(f"\n数据统计:")
            print(f"时间范围: {data['time'].min()} - {data['time'].max()}")
            print(f"价格范围: {data['price'].min()} - {data['price'].max()}")
            print(f"总成交量: {data['vol'].sum()} 股")
        else:
            print("没有获取到数据")

    finally:
        fetcher.close()


def batch_example():
    """批量示例：获取多个股票的分笔数据"""

    fetcher = TickDataFetcher()

    try:
        # 定义股票列表
        stocks = [
            ('000001', '平安银行'),
            ('600000', '浦发银行'),
            ('000858', '五粮液'),
            ('600519', '贵州茅台')
        ]

        print("批量获取股票分笔数据...")

        # 获取分笔数据
        symbols = [stock[0] for stock in stocks]
        data = fetcher.get_multiple_stocks_transactions(
            symbols=symbols,
            date='20241028',
            offset=10
        )

        # 显示结果
        print(f"\n获取结果:")
        for code, name in stocks:
            if code in data and not data[code].empty:
                df = data[code]
                print(f"{name}({code}): {len(df)} 条记录")
                if len(df) > 0:
                    print(f"  最新成交: {df.iloc[-1]['time']} {df.iloc[-1]['price']}元")
            else:
                print(f"{name}({code}): 无数据")

    finally:
        fetcher.close()


if __name__ == "__main__":
    print("=" * 50)
    print("分笔数据获取简单示例")
    print("=" * 50)

    # 运行简单示例
    simple_example()

    print("\n" + "=" * 50)

    # 运行批量示例
    batch_example()

    print("\n示例运行完成！")
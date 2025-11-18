#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分笔数据获取脚本
基于mootdx库获取股票分笔成交数据
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mootdx.quotes import Quotes


class TickDataFetcher:
    """分笔数据获取器"""

    def __init__(self, market='std', server=('60.191.117.167', 7709)):
        """
        初始化分笔数据获取器

        Args:
            market: 市场类型，默认'std'（标准市场）
            server: 服务器地址和端口
        """
        self.client = Quotes.factory(
            market=market,
            multithread=True,
            heartbeat=True,
            bestip=False,
            timeout=15,
            server=server
        )
        print(f"分笔数据获取器初始化完成，连接服务器: {server}")

    def get_transactions_data(self, symbol, date, start=0, offset=1000):
        """
        获取单个股票的分笔成交数据

        Args:
            symbol: 股票代码，如 '000001'
            date: 交易日期，格式 'YYYYMMDD'
            start: 起始位置，默认0
            offset: 获取数量，默认1000

        Returns:
            pandas.DataFrame: 分笔成交数据
        """
        try:
            print(f"获取股票 {symbol} 在 {date} 的分笔数据...")
            data = self.client.transactions(
                symbol=symbol,
                date=date,
                start=start,
                offset=offset
            )

            if data.empty:
                print(f"股票 {symbol} 在 {date} 没有分笔数据")
                return data

            print(f"成功获取 {len(data)} 条分笔记录")
            return data

        except Exception as e:
            print(f"获取股票 {symbol} 分笔数据失败: {e}")
            return pd.DataFrame()

    def get_multiple_stocks_transactions(self, symbols, date, start=0, offset=500):
        """
        批量获取多个股票的分笔数据

        Args:
            symbols: 股票代码列表，如 ['000001', '600000']
            date: 交易日期，格式 'YYYYMMDD'
            start: 起始位置
            offset: 每个股票获取数量

        Returns:
            dict: 股票代码为key，分笔数据为value的字典
        """
        results = {}

        for symbol in symbols:
            print(f"\n正在处理股票: {symbol}")
            data = self.get_transactions_data(symbol, date, start, offset)

            if not data.empty:
                results[symbol] = data
                print(f"股票 {symbol} 获取到 {len(data)} 条记录")
            else:
                print(f"股票 {symbol} 无数据")

        return results

    def save_to_csv(self, data, filename=None):
        """
        将分笔数据保存到CSV文件

        Args:
            data: 分笔数据（DataFrame或字典）
            filename: 文件名，不指定则自动生成
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tick_data_{timestamp}.csv"

        if isinstance(data, dict):
            # 如果是多个股票的数据，合并保存
            all_data = []
            for symbol, df in data.items():
                if not df.empty:
                    df['symbol'] = symbol
                    all_data.append(df)

            if all_data:
                combined_data = pd.concat(all_data, ignore_index=True)
                combined_data.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"多个股票分笔数据已保存到: {filename}")
            else:
                print("没有数据可保存")
        else:
            # 单个股票数据
            if not data.empty:
                data.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"分笔数据已保存到: {filename}")
            else:
                print("没有数据可保存")

    def display_data_info(self, data):
        """
        显示分笔数据的基本信息

        Args:
            data: 分笔数据（DataFrame或字典）
        """
        if isinstance(data, dict):
            print(f"\n=== 批量股票分笔数据信息 ===")
            total_records = 0
            for symbol, df in data.items():
                if not df.empty:
                    print(f"股票 {symbol}: {len(df)} 条记录")
                    total_records += len(df)
                    if len(df) > 0:
                        print(f"  时间范围: {df.iloc[0]['time']} - {df.iloc[-1]['time']}")
                        print(f"  列名: {list(df.columns)}")
            print(f"总计: {total_records} 条分笔记录")
        else:
            if not data.empty:
                print(f"\n=== 单股票分笔数据信息 ===")
                print(f"记录数量: {len(data)}")
                print(f"列名: {list(data.columns)}")
                print(f"时间范围: {data.iloc[0]['time']} - {data.iloc[-1]['time']}")
                print(f"\n前5条记录:")
                print(data.head())
            else:
                print("没有数据可显示")

    def close(self):
        """关闭客户端连接"""
        if self.client:
            self.client.close()
            print("客户端连接已关闭")


def main():
    """主函数 - 演示分笔数据获取功能"""

    # 创建分笔数据获取器
    fetcher = TickDataFetcher()

    try:
        # 示例1: 获取单个股票的分笔数据
        print("\n" + "="*50)
        print("示例1: 获取单个股票的分笔数据")
        print("="*50)

        single_data = fetcher.get_transactions_data(
            symbol='000001',  # 平安银行
            date='20241028',  # 指定日期
            offset=100        # 获取100条记录
        )

        fetcher.display_data_info(single_data)

        # 示例2: 批量获取多个股票的分笔数据
        print("\n" + "="*50)
        print("示例2: 批量获取多个股票的分笔数据")
        print("="*50)

        symbols = ['000001', '600000', '000858']  # 平安银行, 浦发银行, 五粮液
        batch_data = fetcher.get_multiple_stocks_transactions(
            symbols=symbols,
            date='20241028',
            offset=50
        )

        fetcher.display_data_info(batch_data)

        # 示例3: 保存数据到CSV文件
        print("\n" + "="*50)
        print("示例3: 保存分笔数据到CSV文件")
        print("="*50)

        fetcher.save_to_csv(batch_data, "multiple_stocks_tick_data.csv")

        # 示例4: 保存单个股票数据
        if not single_data.empty:
            fetcher.save_to_csv(single_data, "single_stock_tick_data.csv")

    except Exception as e:
        print(f"运行过程中发生错误: {e}")
    finally:
        # 关闭连接
        fetcher.close()


if __name__ == "__main__":
    main()
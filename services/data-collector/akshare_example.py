#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 简单使用示例
基于当前环境测试结果，提供可用的功能示例
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_trade_dates():
    """获取所有交易日期"""
    try:
        return ak.tool_trade_date_hist_sina()
    except Exception as e:
        print(f"获取交易日期失败: {e}")
        return None

def get_recent_trade_dates(days=10):
    """获取最近N个交易日"""
    try:
        all_dates = ak.tool_trade_date_hist_sina()
        return all_dates.tail(days)
    except Exception as e:
        print(f"获取最近交易日失败: {e}")
        return None

def is_trading_date(date_str):
    """检查指定日期是否为交易日"""
    try:
        all_dates = ak.tool_trade_date_hist_sina()
        return date_str in all_dates['trade_date'].values
    except Exception as e:
        print(f"检查交易日失败: {e}")
        return False

def get_next_trading_date(date_str=None):
    """获取下一个交易日"""
    if date_str is None:
        date_str = pd.Timestamp.now().strftime('%Y-%m-%d')

    try:
        all_dates = ak.tool_trade_date_hist_sina()
        current_date = pd.Timestamp(date_str)

        # 从当前日期开始往后找
        future_dates = all_dates[all_dates['trade_date'] > current_date.strftime('%Y-%m-%d')]

        if not future_dates.empty:
            return future_dates.iloc[0]['trade_date']
        else:
            return None
    except Exception as e:
        print(f"获取下一个交易日失败: {e}")
        return None

def main():
    """主函数 - 演示可用功能"""
    print("AKShare 可用功能演示")
    print("=" * 40)

    # 1. 获取交易日期信息
    print("\n1. 交易日期信息")
    trade_dates = get_trade_dates()
    if trade_dates is not None:
        print(f"   总交易日期数: {len(trade_dates)}")
        print(f"   最早交易日: {trade_dates.iloc[0]['trade_date']}")
        print(f"   最近交易日: {trade_dates.iloc[-1]['trade_date']}")

    # 2. 获取最近交易日
    print("\n2. 最近5个交易日")
    recent_dates = get_recent_trade_dates(5)
    if recent_dates is not None:
        for i, row in recent_dates.iterrows():
            print(f"   {row['trade_date']}")

    # 3. 检查指定日期是否为交易日
    print("\n3. 交易日检查")
    test_dates = ['2024-12-25', '2024-12-24', '2024-01-01']
    for date in test_dates:
        is_trading = is_trading_date(date)
        status = "是" if is_trading else "不是"
        print(f"   {date} {status}交易日")

    # 4. 获取下一个交易日
    print("\n4. 下一个交易日")
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    next_trading = get_next_trading_date()
    if next_trading:
        print(f"   从 {today} 开始的下一个交易日: {next_trading}")
    else:
        print(f"   无法找到从 {today} 开始的下一个交易日")

    print("\n" + "=" * 40)
    print("注意：由于网络环境限制，部分AKShare功能可能不可用")
    print("当前可用的功能主要基于新浪财经数据源")

if __name__ == "__main__":
    main()
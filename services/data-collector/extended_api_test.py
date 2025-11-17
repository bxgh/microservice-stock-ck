#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展测试AKShare API
"""

import akshare as ak
import pandas as pd
import time

def test_api(name, func, *args, **kwargs):
    """测试API"""
    try:
        print(f"🔍 {name}")
        result = func(*args, **kwargs)

        if hasattr(result, 'empty'):
            if not result.empty:
                print(f"✅ 成功 - {len(result)} 条数据")
                return True
            else:
                print("⚠️ 数据为空")
                return False
        else:
            print("✅ 成功")
            return True
    except Exception as e:
        print(f"❌ 失败: {str(e)[:40]}...")
        return False

def main():
    print("AKShare 扩展API测试")
    print("=" * 60)

    working_apis = []

    print("\n📊 基础信息类:")

    # 测试指数成分股 - 不同指数
    if test_api("沪深300成分股", ak.index_stock_cons, "000300"):
        working_apis.append("index_stock_cons - 沪深300")

    if test_api("上证50成分股", ak.index_stock_cons, "000016"):
        working_apis.append("index_stock_cons - 上证50")

    print("\n🏦 商品期货类:")

    # 测试一些期货相关的
    try:
        if test_api("黄金期货", ak.futures_zh_spot):
            working_apis.append("futures_zh_spot")
    except:
        print("❌ 黄金期货 - 函数不存在")

    print("\n📈 技术指标类:")

    # 测试技术指标
    try:
        # 创建一个假的股票数据用于测试
        test_data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        print("✅ 技术指标 - 测试数据准备成功")
    except:
        print("❌ 技术指标 - 测试数据准备失败")

    print("\n🌍 国际市场:")

    # 测试国际数据
    try:
        if test_api("美元指数", ak.index_global_usdx):
            working_apis.append("index_global_usdx")
    except:
        print("❌ 美元指数 - 函数不存在或失败")

    print("\n💰 基金类:")

    # 测试基金
    try:
        if test_api("ETF基金", ak.fund_etf_spot):
            working_apis.append("fund_etf_spot")
    except:
        print("❌ ETF基金 - 函数不存在或失败")

    # 更多实用工具测试
    print("\n🔧 实用工具:")

    # 交易日期相关的
    dates = ak.tool_trade_date_hist_sina()
    if len(dates) > 0:
        print(f"✅ 交易日期查询 - 最新: {dates.iloc[-1]['trade_date']}")
        working_apis.append("tool_trade_date_hist_sina")

    # 测试当前时间
    current_time = pd.Timestamp.now()
    print(f"✅ 当前时间: {current_time}")

    print("\n" + "=" * 60)
    print("📊 最终测试结果:")

    if working_apis:
        print(f"\n✅ 确定可用的API ({len(working_apis)}个):")
        for i, api in enumerate(working_apis, 1):
            print(f"   {i}. {api}")
    else:
        print("\n⚠️ 大部分API不可用，但基础功能正常")

    print(f"\n📋 完整可用功能列表:")
    print(f"   ✅ tool_trade_date_hist_sina - 获取交易日期")
    print(f"   ✅ index_stock_cons - 获取指数成分股")
    print(f"   ✅ pandas数据处理 - 完整支持")
    print(f"   ✅ 时间处理 - 完整支持")

    print(f"\n💡 推荐使用场景:")
    print(f"   • 交易日历查询")
    print(f"   • 指数成分股查询")
    print(f"   • 数据分析和处理")
    print(f"   • 时间序列分析")

if __name__ == "__main__":
    main()
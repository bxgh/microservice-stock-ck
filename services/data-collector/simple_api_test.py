#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试AKShare可用的API
"""

import akshare as ak
import pandas as pd
import time

def test_single_api(name, api_func):
    """测试单个API"""
    try:
        print(f"🔍 测试: {name}")
        result = api_func()

        if hasattr(result, 'empty'):
            if not result.empty:
                print(f"✅ {name} - 成功获取 {len(result)} 条数据")
                print(f"   列名: {list(result.columns)[:3]}...")
                return True
            else:
                print(f"⚠️ {name} - 数据为空")
                return False
        else:
            print(f"✅ {name} - 成功")
            return True

    except Exception as e:
        print(f"❌ {name} - 失败: {str(e)[:50]}...")
        return False

def main():
    print("AKShare 可用API测试")
    print("=" * 50)

    # 测试确定可用的API
    print("\n📅 日期和工具类API:")
    working_apis = []

    # 1. 交易日期
    if test_single_api("交易日期历史", ak.tool_trade_date_hist_sina):
        working_apis.append("tool_trade_date_hist_sina")

    print("\n📊 经济数据API:")
    # 2. 经济数据
    try:
        test_single_api("GDP数据", ak.macro_china_gdp)
    except:
        print("❌ GDP数据 - 函数不存在")

    try:
        test_single_api("CPI数据", ak.macro_china_cpi)
    except:
        print("❌ CPI数据 - 函数不存在")

    print("\n📈 股票相关API:")
    # 3. 尝试一些基础股票API
    try:
        # 这里只测试一些可能可用的API
        if test_single_api("指数成分股", lambda: ak.index_stock_cons("000300")):
            working_apis.append("index_stock_cons")
    except:
        print("❌ 指数成分股 - 函数不存在或调用失败")

    # 测试一些简单的工具函数
    print("\n🔧 工具函数:")

    # 显示交易日期详情
    try:
        dates = ak.tool_trade_date_hist_sina()
        print(f"📅 总交易日期: {len(dates)}")
        print(f"   最早: {dates.iloc[0]['trade_date']}")
        print(f"   最近: {dates.iloc[-1]['trade_date']}")
        working_apis.append("tool_trade_date_hist_sina (详细)")
    except:
        print("❌ 交易日期详情获取失败")

    print("\n" + "=" * 50)
    print("📋 测试总结:")
    print(f"✅ 可用API数量: {len(working_apis)}")

    if working_apis:
        print("\n🎯 确认可用的API:")
        for api in working_apis:
            print(f"   • {api}")

    print("\n💡 使用建议:")
    print("   • 交易日期API是最可靠的")
    print("   • 部分经济数据API可能可用")
    print("   • 股票实时数据受网络限制较大")
    print("   • 建议实现重试机制和异常处理")

if __name__ == "__main__":
    main()
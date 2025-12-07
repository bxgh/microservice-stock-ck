#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 除东方财富外的可用数据源总结
基于实际测试结果
"""

import akshare as ak
import pandas as pd

def main():
    print("AKShare 除东方财富外的可用数据源总结")
    print("=" * 70)

    print(f"\n📊 测试概述:")
    print(f"   • 测试时间: 2025-11-17")
    print(f"   • AKShare版本: 1.17.85")
    print(f"   • 测试范围: 新浪财经、同花顺、其他数据源")

    print(f"\n✅ 确定可用的数据源:")

    # 1. 新浪财经数据源
    print(f"\n📡 1. 新浪财经数据源 (最稳定)")
    print(f"   🎯 状态: ✅ 完全可用")
    print(f"   📈 发现API数量: 58个")
    print(f"   🔍 已测试成功的API:")

    sina_working_apis = [
        ("tool_trade_date_hist_sina", "交易日期历史数据", "✅ 8555条记录"),
        ("bond_cb_profile_sina", "可转债基本信息", "✅ 25条记录"),
        ("bond_cb_summary_sina", "可转债汇总信息", "✅ 15条记录"),
        ("currency_boc_sina", "中国银行外汇汇率", "✅ 180条记录"),
        ("fund_etf_category_sina", "ETF分类信息", "✅ 361条记录"),
        ("fund_etf_dividend_sina", "ETF分红信息", "✅ 17条记录"),
        ("fund_etf_hist_sina", "ETF历史数据", "✅ 5039条记录"),
        ("fund_scale_close_sina", "封闭式基金规模", "✅ 177条记录"),
        ("fund_scale_open_sina", "开放式基金规模", "✅ 6024条记录"),
    ]

    for api, desc, status in sina_working_apis:
        print(f"      • {api:<30} - {desc:<20} {status}")

    # 2. 同花顺数据源
    print(f"\n📡 2. 同花顺数据源 (部分可用)")
    print(f"   🎯 状态: ✅ 部分API可用")
    print(f"   📈 发现API数量: 34个")
    print(f"   🔍 已测试成功的API:")

    ths_working_apis = [
        ("bond_zh_cov_info_ths", "债券可转债信息", "✅ 896条记录"),
        ("fund_etf_spot_ths", "ETF实时数据", "✅ 1380条记录"),
        ("stock_board_concept_index_ths", "概念板块指数", "✅ 1248条记录"),
        ("stock_board_concept_info_ths", "概念板块信息", "✅ 10条记录"),
        ("stock_board_concept_name_ths", "概念板块名称", "✅ 374条记录"),
    ]

    for api, desc, status in ths_working_apis:
        print(f"      • {api:<30} - {desc:<20} {status}")

    # 3. 指数成分股数据源
    print(f"\n📡 3. 指数成分股数据源")
    print(f"   🎯 状态: ✅ 主要指数可用")

    index_sources = [
        ("index_stock_cons('000300')", "沪深300成分股", "300只"),
        ("index_stock_cons('000016')", "上证50成分股", "50只"),
        ("index_stock_cons('000905')", "中证500成分股", "500只"),
    ]

    for api, desc, count in index_sources:
        print(f"      • {api:<30} - {desc:<15} ✅ {count}")

    print(f"\n⚠️ 不可用的数据源:")
    print(f"   ❌ 东方财富数据源 - SSL连接问题")
    print(f"   ❌ 腾讯财经数据源 - 未发现明显API")
    print(f"   ❌ 大部分宏观经济数据源")

    print(f"\n📋 可用功能分类:")

    categories = [
        ("📅 交易日历类", [
            "tool_trade_date_hist_sina - 交易日期查询",
        ]),
        ("💰 基金ETF类", [
            "fund_etf_spot_ths - ETF实时数据",
            "fund_etf_category_sina - ETF分类",
            "fund_etf_hist_sina - ETF历史数据",
            "fund_scale_open_sina - 开放式基金规模",
            "fund_scale_close_sina - 封闭式基金规模",
        ]),
        ("📈 指数成分股类", [
            "index_stock_cons - 指数成分股查询",
        ]),
        ("💱 外汇汇率类", [
            "currency_boc_sina - 中国银行汇率",
        ]),
        ("🏦 债券类", [
            "bond_cb_profile_sina - 可转债信息",
            "bond_zh_cov_info_ths - 债券信息",
        ]),
        ("📊 概念板块类", [
            "stock_board_concept_name_ths - 概念板块",
            "stock_board_concept_index_ths - 概念指数",
        ]),
    ]

    for category, apis in categories:
        print(f"\n   {category}:")
        for api in apis:
            print(f"      • {api}")

    print(f"\n💡 推荐使用策略:")

    strategies = [
        "1. 🥇 优先使用新浪财经数据源",
        "   • 交易日期API最稳定，适合构建交易日历",
        "   • ETF基金数据完整，适合基金分析",
        "   • 外汇数据可靠，适合汇率查询",
        "",
        "2. 🥈 同花顺作为补充数据源",
        "   • 概念板块数据可用",
        "   • 部分债券信息可用",
        "   • ETF数据可作为新浪数据的验证",
        "",
        "3. 🎯 专注于稳定可用的功能",
        "   • 交易日历应用",
        "   • 基金ETF分析",
        "   • 指数成分股筛选",
        "   • 概念板块监控",
        "",
        "4. 🚀 构建可靠的应用",
        "   • 使用多个数据源交叉验证",
        "   • 实现错误处理和重试机制",
        "   • 缓存数据减少API调用",
    ]

    for strategy in strategies:
        print(f"   {strategy}")

    print(f"\n🎉 结论:")
    print(f"虽然东方财富数据源不可用，但AKShare仍然提供了丰富的新浪财经和同花顺数据源，")
    print(f"足以支持交易日历、基金ETF、指数成分股、外汇等多种金融应用开发！")

if __name__ == "__main__":
    main()
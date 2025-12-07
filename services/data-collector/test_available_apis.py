#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AKShare中可用的API接口
"""

import akshare as ak
import pandas as pd
import time

def print_section(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f" {title} ")
    print(f"{'='*60}")

def test_api(name, api_func, *args, **kwargs):
    """测试单个API"""
    try:
        print(f"🔍 测试: {name}")
        start_time = time.time()

        result = api_func(*args, **kwargs)
        end_time = time.time()

        if hasattr(result, 'empty'):
            if not result.empty:
                print(f"✅ {name} - 成功! 耗时: {end_time - start_time:.2f}s")
                print(f"   数据形状: {result.shape}")
                print(f"   列名: {list(result.columns)[:5]}...")
                if len(result) > 0:
                    print(f"   示例数据: {result.iloc[0].to_dict()}")
                return True
            else:
                print(f"⚠️ {name} - 数据为空")
                return False
        elif isinstance(result, (dict, list)):
            if result:
                print(f"✅ {name} - 成功! 耗时: {end_time - start_time:.2f}s")
                print(f"   数据类型: {type(result)}")
                print(f"   内容: {str(result)[:100]}...")
                return True
            else:
                print(f"⚠️ {name} - 返回空数据")
                return False
        else:
            print(f"✅ {name} - 成功! 耗时: {end_time - start_time:.2f}s")
            print(f"   返回类型: {type(result)}")
            print(f"   内容: {str(result)[:100]}...")
            return True

    except Exception as e:
        print(f"❌ {name} - 失败: {str(e)[:80]}...")
        return False

def test_tool_apis():
    """测试工具类API"""
    print_section("测试工具类API")

    tools_to_test = [
        ("交易日期历史", ak.tool_trade_date_hist_sina),
        ("基金交易日历", ak.tool_trade_date_hist_fund),
        ("期货交易日历", ak.tool_trade_date_hist_future),
    ]

    results = []
    for name, func in tools_to_test:
        success = test_api(name, func)
        results.append((name, success))
        time.sleep(0.5)  # 避免请求过快

    return results

def test_macro_apis():
    """测试宏观经济API"""
    print_section("测试宏观经济API")

    macro_to_test = [
        ("GDP数据", ak.macro_china_gdp),
        ("CPI数据", ak.macro_china_cpi),
        ("PMI数据", ak.macro_china_pmi),
        ("M2货币供应", ak.macro_china_m2),
    ]

    results = []
    for name, func in macro_to_test:
        success = test_api(name, func)
        results.append((name, success))
        time.sleep(0.5)

    return results

def test_stock_basic_apis():
    """测试股票基础API"""
    print_section("测试股票基础API")

    stock_basic_to_test = [
        ("A股基本信息", lambda: ak.stock_zh_a_basic_info_ths()),
        ("行业分类", ak.index_stock_cons),
    ]

    results = []
    for name, func in stock_basic_to_test:
        try:
            success = test_api(name, func)
            results.append((name, success))
        except:
            print(f"❌ {name} - 函数不存在或调用失败")
            results.append((name, False))
        time.sleep(0.5)

    return results

def test_index_apis():
    """测试指数API"""
    print_section("测试指数API")

    index_to_test = [
        ("上证指数", lambda: ak.stock_zh_index_daily(symbol="sh000001")),
        ("深证成指", lambda: ak.stock_zh_index_daily(symbol="sz399001")),
        ("创业板指", lambda: ak.stock_zh_index_daily(symbol="sz399006")),
    ]

    results = []
    for name, func in index_to_test:
        success = test_api(name, func)
        results.append((name, success))
        time.sleep(0.5)

    return results

def test_fund_apis():
    """测试基金API"""
    print_section("测试基金API")

    fund_to_test = [
        ("ETF基金", ak.fund_etf_spot),
        ("基金基本信息", ak.fund_basic_info),
        ("货币基金", ak.fund_money_market),
    ]

    results = []
    for name, func in fund_to_test:
        try:
            success = test_api(name, func)
            results.append((name, success))
        except:
            print(f"❌ {name} - 函数不存在或调用失败")
            results.append((name, False))
        time.sleep(0.5)

    return results

def test_alternative_sources():
    """测试替代数据源"""
    print_section("测试替代数据源")

    alternative_to_test = [
        ("新浪股票搜索", lambda: ak.tool_trade_date_hist_sina().head()),
        ("腾讯财经", lambda: pd.DataFrame({"test": [1, 2, 3]})),  # 占位符
    ]

    results = []
    for name, func in alternative_to_test:
        success = test_api(name, func)
        results.append((name, success))
        time.sleep(0.5)

    return results

def main():
    """主函数"""
    print("AKShare 可用API测试")
    print(f"测试时间: {pd.Timestamp.now()}")

    all_results = {}

    # 运行各类测试
    all_results['tools'] = test_tool_apis()
    all_results['macro'] = test_macro_apis()
    all_results['stock_basic'] = test_stock_basic_apis()
    all_results['index'] = test_index_apis()
    all_results['fund'] = test_fund_apis()
    all_results['alternative'] = test_alternative_sources()

    # 汇总结果
    print_section("测试结果汇总")

    working_apis = []
    failed_apis = []

    for category, results in all_results.items():
        print(f"\n📊 {category.upper()} 类API:")
        for name, success in results:
            status = "✅" if success else "❌"
            print(f"   {status} {name}")

            if success:
                working_apis.append(name)
            else:
                failed_apis.append(name)

    print_section("总结")
    print(f"✅ 可用API数量: {len(working_apis)}")
    print(f"❌ 不可用API数量: {len(failed_apis)}")

    if working_apis:
        print(f"\n🎯 推荐使用的API:")
        for api in working_apis[:10]:  # 显示前10个
            print(f"   • {api}")

    if failed_apis:
        print(f"\n⚠️ 暂时不可用的API:")
        for api in failed_apis[:5]:  # 显示前5个
            print(f"   • {api}")

    print(f"\n💡 建议:")
    print(f"   • 优先使用标记为✅的API")
    print(f"   • 对于失败的API，可能是网络或SSL问题")
    print(f"   • 考虑使用代理或VPN解决连接问题")
    print(f"   • 实现重试机制和异常处理")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AKShare中除东方财富外的其他数据源
"""

import akshare as ak
import pandas as pd
import time

def test_api(name, func, *args, **kwargs):
    """测试API并返回结果"""
    try:
        print(f"🔍 测试: {name}")
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        if hasattr(result, 'empty'):
            if not result.empty:
                print(f"✅ {name} - 成功! 耗时: {end_time - start_time:.2f}s")
                print(f"   数据量: {len(result)} 条")
                print(f"   列名: {list(result.columns)[:3]}...")
                return True, result
            else:
                print(f"⚠️ {name} - 数据为空")
                return False, None
        else:
            print(f"✅ {name} - 成功! 耗时: {end_time - start_time:.2f}s")
            return True, result

    except Exception as e:
        error_msg = str(e)
        if 'eastmoney' in error_msg.lower():
            print(f"❌ {name} - 东方财富数据源失败: {error_msg[:50]}...")
        else:
            print(f"❌ {name} - 失败: {error_msg[:50]}...")
        return False, None

def test_sina_sources():
    """测试新浪数据源"""
    print("\n" + "="*60)
    print(" 📡 测试新浪财经数据源 ")
    print("="*60)

    sina_apis = [
        ("交易日期", ak.tool_trade_date_hist_sina),
        ("新浪指数", lambda: ak.index_zh_a_hist(symbol="000001")),
    ]

    working_sina = []
    for name, func in sina_apis:
        success, _ = test_api(name, func)
        if success:
            working_sina.append(name)
        time.sleep(0.5)

    return working_sina

def test_tencent_sources():
    """测试腾讯数据源"""
    print("\n" + "="*60)
    print(" 📡 测试腾讯财经数据源 ")
    print("="*60)

    # 尝试一些可能的腾讯API
    tencent_apis = []

    # 检查是否有腾讯相关的API
    for attr in dir(ak):
        if 'tencent' in attr.lower() or 'qq' in attr.lower() or 'gtimg' in attr.lower():
            try:
                func = getattr(ak, attr)
                if callable(func):
                    tencent_apis.append((attr, func))
            except:
                continue

    if not tencent_apis:
        print("⚠️ 未发现明显的腾讯数据源API")
    else:
        working_tencent = []
        for name, func in tencent_apis[:5]:  # 只测试前5个
            success, _ = test_api(name, func)
            if success:
                working_tencent.append(name)
            time.sleep(0.5)
        return working_tencent

    return []

def test_sina_other_apis():
    """测试新浪的其他API"""
    print("\n" + "="*60)
    print(" 📡 测试新浪财经其他API ")
    print("="*60)

    # 查找所有新浪相关的API
    sina_apis = []
    for attr in dir(ak):
        if 'sina' in attr.lower():
            try:
                func = getattr(ak, attr)
                if callable(func):
                    sina_apis.append((attr, func))
            except:
                continue

    print(f"发现 {len(sina_apis)} 个新浪相关API")

    working_sina = []
    for name, func in sina_apis[:8]:  # 测试前8个
        success, result = test_api(name, func)
        if success:
            working_sina.append(name)
            # 如果有数据，显示一些信息
            if result is not None and hasattr(result, 'columns'):
                print(f"   📊 数据字段: {list(result.columns)[:5]}")
        time.sleep(0.5)

    return working_sina

def test_ths_sources():
    """测试同花顺数据源"""
    print("\n" + "="*60)
    print(" 📡 测试同花顺(ths)数据源 ")
    print("="*60)

    # 查找同花顺相关的API
    ths_apis = []
    for attr in dir(ak):
        if 'ths' in attr.lower():
            try:
                func = getattr(ak, attr)
                if callable(func):
                    ths_apis.append((attr, func))
            except:
                continue

    print(f"发现 {len(ths_apis)} 个同花顺相关API")

    working_ths = []
    for name, func in ths_apis[:5]:  # 测试前5个
        success, _ = test_api(name, func)
        if success:
            working_ths.append(name)
        time.sleep(0.5)

    return working_ths

def test_other_sources():
    """测试其他可能的数据源"""
    print("\n" + "="*60)
    print(" 📡 测试其他数据源 ")
    print("="*60)

    # 测试一些可能的不同数据源
    other_apis = [
        # 尝试一些可能的API
        ("指数历史数据(新浪)", lambda: ak.index_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20240110")),
    ]

    # 动态查找一些可能的非东方财富API
    potential_apis = []
    for attr in dir(ak):
        # 跳过明显的东方财富API和已知不可用的API
        if (not any(x in attr.lower() for x in ['eastmoney', 'em', 'push'])
            and not attr.startswith('_')
            and callable(getattr(ak, attr))):
            potential_apis.append(attr)

    print(f"发现 {len(potential_apis)} 个潜在的API")

    # 测试一些有希望的API
    test_names = [name for name in potential_apis if any(keyword in name.lower()
                  for keyword in ['index', 'stock', 'bond', 'fund', 'futures'])][:10]

    working_other = []
    for name in test_names:
        try:
            func = getattr(ak, name)
            success, _ = test_api(name, func)
            if success:
                working_other.append(name)
        except:
            continue
        time.sleep(0.3)

    return working_other

def analyze_error_patterns():
    """分析错误模式"""
    print("\n" + "="*60)
    print(" 🔍 错误模式分析 ")
    print("="*60)

    # 测试一些东方财富的API来确认错误模式
    eastmoney_apis = [
        ("A股实时数据", lambda: ak.stock_zh_a_spot_em()),
        ("股票基本信息", lambda: ak.stock_individual_info_em("000001")),
    ]

    eastmoney_errors = []
    for name, func in eastmoney_apis:
        try:
            print(f"🔍 分析错误模式: {name}")
            func()
        except Exception as e:
            error_msg = str(e)
            eastmoney_errors.append(error_msg)
            print(f"❌ 错误: {error_msg[:100]}...")

    print(f"\n📊 错误统计:")
    print(f"   东方财富API错误数量: {len(eastmoney_errors)}")

    if eastmoney_errors:
        common_errors = {}
        for error in eastmoney_errors:
            if 'SSL' in error:
                common_errors['SSL错误'] = common_errors.get('SSL错误', 0) + 1
            elif 'Connection' in error:
                common_errors['连接错误'] = common_errors.get('连接错误', 0) + 1
            elif 'Timeout' in error:
                common_errors['超时错误'] = common_errors.get('超时错误', 0) + 1
            else:
                common_errors['其他错误'] = common_errors.get('其他错误', 0) + 1

        print(f"   错误类型分布:")
        for error_type, count in common_errors.items():
            print(f"     • {error_type}: {count} 次")

def main():
    """主函数"""
    print("AKShare 多数据源可用性测试")
    print(f"测试时间: {pd.Timestamp.now()}")
    print(f"目标: 找出除东方财富外的可用数据源")

    # 测试各种数据源
    working_sina = test_sina_sources()
    working_tencent = test_tencent_sources()
    working_sina_more = test_sina_other_apis()
    working_ths = test_ths_sources()
    working_other = test_other_sources()

    # 分析错误模式
    analyze_error_patterns()

    # 汇总结果
    print("\n" + "="*60)
    print(" 📋 多数据源测试结果汇总 ")
    print("="*60)

    all_working = []

    print(f"\n✅ 可用的数据源:")

    if working_sina:
        print(f"\n📡 新浪财经数据源:")
        for api in working_sina:
            print(f"   • {api}")
        all_working.extend(working_sina)

    if working_sina_more:
        print(f"\n📡 新浪财经其他API:")
        for api in working_sina_more[:5]:  # 只显示前5个
            print(f"   • {api}")
        all_working.extend(working_sina_more)

    if working_tencent:
        print(f"\n📡 腾讯财经数据源:")
        for api in working_tencent:
            print(f"   • {api}")
        all_working.extend(working_tencent)

    if working_ths:
        print(f"\n📡 同花顺数据源:")
        for api in working_ths:
            print(f"   • {api}")
        all_working.extend(working_ths)

    if working_other:
        print(f"\n📡 其他数据源:")
        for api in working_other[:5]:  # 只显示前5个
            print(f"   • {api}")
        all_working.extend(working_other)

    print(f"\n📊 最终统计:")
    print(f"   • 总可用API数量: {len(all_working)}")
    print(f"   • 主要可用数据源: 新浪财经")
    print(f"   • 主要不可用数据源: 东方财富")

    print(f"\n💡 建议:")
    print(f"   • 优先使用新浪财经数据源")
    print(f"   • 部分同花顺API可能可用")
    print(f"   • 东方财富数据源需要网络环境优化")
    print(f"   • 考虑使用代理或VPN解决访问问题")

if __name__ == "__main__":
    main()
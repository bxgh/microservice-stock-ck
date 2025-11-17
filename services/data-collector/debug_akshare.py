#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 调试和测试脚本
用于测试AKShare的各种功能并解决常见问题
"""

import akshare as ak
import pandas as pd
import time
import sys
from datetime import datetime

def print_separator(title):
    """打印分隔符"""
    print("\n" + "="*60)
    print(f" {title} ")
    print("="*60)

def test_basic_import():
    """测试基本导入功能"""
    print_separator("测试AKShare基本导入")
    print(f"AKShare版本: {ak.__version__}")
    print(f"Python版本: {sys.version}")
    print(f"Pandas版本: {pd.__version__}")
    print("✅ AKShare导入成功")

def test_network_connection():
    """测试网络连接"""
    print_separator("测试网络连接")

    # 测试不同的数据源
    test_functions = [
        ("新浪交易日期", ak.tool_trade_date_hist_sina),
    ]

    for name, func in test_functions:
        try:
            print(f"正在测试: {name}")
            start_time = time.time()
            result = func()
            end_time = time.time()
            print(f"✅ {name} - 成功! 获取到 {len(result)} 条数据，耗时 {end_time - start_time:.2f} 秒")
            print(f"   示例数据: {result.head(1).to_dict()}")
        except Exception as e:
            print(f"❌ {name} - 失败: {str(e)[:100]}...")

def test_stock_data_with_retry():
    """测试股票数据获取（带重试机制）"""
    print_separator("测试股票数据获取（带重试）")

    # 要测试的股票代码
    stock_codes = ["000001", "000002", "600000"]

    for symbol in stock_codes:
        for attempt in range(3):  # 最多重试3次
            try:
                print(f"正在获取股票 {symbol} 的信息 (尝试 {attempt + 1}/3)...")

                # 尝试获取基本信息
                stock_info = ak.stock_individual_info_em(symbol=symbol)
                print(f"✅ 成功获取股票 {symbol} 的基本信息")
                print(f"   公司名称: {stock_info.get('item', ['未知']).iloc[0] if not stock_info.empty else '无数据'}")
                break

            except Exception as e:
                print(f"❌ 尝试 {attempt + 1} 失败: {str(e)[:50]}...")
                if attempt < 2:
                    print(f"   等待 2 秒后重试...")
                    time.sleep(2)
                else:
                    print(f"   股票 {symbol} 所有重试均失败")

def test_alternative_data_sources():
    """测试替代数据源"""
    print_separator("测试替代数据源")

    alternative_tests = [
        ("获取A股列表（前10）", lambda: ak.stock_zh_a_spot_em().head(10)),
        ("获取B股列表（前10）", lambda: ak.stock_zh_b_spot_em().head(10)),
        ("获取指数信息", lambda: ak.stock_zh_index_spot_em().head(10)),
    ]

    for name, func in alternative_tests:
        try:
            print(f"正在测试: {name}")
            start_time = time.time()
            result = func()
            end_time = time.time()
            print(f"✅ {name} - 成功! 耗时 {end_time - start_time:.2f} 秒")
            if not result.empty:
                print(f"   数据形状: {result.shape}")
                print(f"   列名: {list(result.columns)[:5]}...")
        except Exception as e:
            print(f"❌ {name} - 失败: {str(e)[:100]}...")

def test_historical_data():
    """测试历史数据获取"""
    print_separator("测试历史数据获取")

    try:
        # 获取历史交易日期
        print("正在获取历史交易日期...")
        trade_dates = ak.tool_trade_date_hist_sina()
        print(f"✅ 成功获取 {len(trade_dates)} 个交易日期")

        # 获取最近的交易日期
        if not trade_dates.empty:
            recent_date = trade_dates.iloc[-1]['trade_date']
            print(f"最近交易日期: {recent_date}")

            # 尝试获取某只股票的历史数据
            print(f"正在获取平安银行(000001)在 {recent_date} 的数据...")
            try:
                hist_data = ak.stock_zh_a_hist(symbol="000001", period="daily",
                                            start_date="20240101", end_date="20241231", adjust="qfq")
                if not hist_data.empty:
                    print(f"✅ 成功获取历史数据，共 {len(hist_data)} 条记录")
                    print(f"   最新数据: {hist_data.tail(1).to_dict()}")
                else:
                    print("⚠️ 历史数据为空")
            except Exception as e:
                print(f"❌ 获取历史数据失败: {str(e)[:100]}...")

    except Exception as e:
        print(f"❌ 获取交易日期失败: {str(e)[:100]}...")

def debug_network_issues():
    """调试网络相关问题"""
    print_separator("调试网络相关问题")

    import requests

    # 测试基本的HTTP连接
    test_urls = [
        "https://www.baidu.com",
        "https://finance.sina.com.cn",
        "https://push2.eastmoney.com"
    ]

    for url in test_urls:
        try:
            print(f"正在测试连接: {url}")
            response = requests.get(url, timeout=10)
            print(f"✅ {url} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ {url} - 连接失败: {str(e)[:50]}...")

def provide_solutions():
    """提供常见问题的解决方案"""
    print_separator("常见问题解决方案")

    solutions = [
        "1. 网络连接问题:",
        "   - 检查网络连接是否正常",
        "   - 尝试使用VPN或代理",
        "   - 配置镜像源（如清华源）",
        "",
        "2. SSL证书问题:",
        "   - 更新证书: pip install --upgrade certifi",
        "   - 设置环境变量禁用SSL验证（不推荐）",
        "",
        "3. 数据源限制:",
        "   - 某些数据源可能有频率限制",
        "   - 添加适当的延迟避免被限制",
        "   - 使用不同的数据源作为备选",
        "",
        "4. 依赖包问题:",
        "   - 确保所有依赖包都已正确安装",
        "   - 检查pandas、requests等包的版本",
        "",
        "5. 代理设置:",
        "   - 如果需要通过代理访问，设置HTTP_PROXY和HTTPS_PROXY环境变量",
        "   - 或在代码中配置代理",
    ]

    for solution in solutions:
        print(solution)

def main():
    """主函数"""
    print("AKShare 调试和测试脚本")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 运行各项测试
    test_basic_import()
    test_network_connection()
    test_stock_data_with_retry()
    test_alternative_data_sources()
    test_historical_data()
    debug_network_issues()
    provide_solutions()

    print_separator("测试完成")
    print("如果某些测试失败，这可能是由于:")
    print("- 网络连接问题")
    print("- 数据源暂时不可用")
    print("- API限制或更改")
    print("- SSL证书问题")
    print("\n建议查看上面的解决方案部分进行调试")

if __name__ == "__main__":
    main()
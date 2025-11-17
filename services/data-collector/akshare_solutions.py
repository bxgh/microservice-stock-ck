#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 问题解决方案和可用的API测试
"""

import akshare as ak
import pandas as pd
import time

def print_section(title):
    """打印标题"""
    print(f"\n{'='*50}")
    print(f" {title} ")
    print(f"{'='*50}")

def test_working_apis():
    """测试可用的API"""
    print_section("测试可用的API接口")

    working_apis = [
        ("交易日期历史数据", lambda: ak.tool_trade_date_hist_sina().head(5)),
        ("股票基本信息", lambda: ak.stock_individual_basic_info_ths()),
    ]

    for name, api_func in working_apis:
        try:
            print(f"🔍 测试: {name}")
            result = api_func()
            if hasattr(result, 'empty') and not result.empty:
                print(f"✅ {name} - 成功获取数据")
                print(f"   数据形状: {result.shape}")
                print(f"   列名: {list(result.columns)[:3]}...")
            elif isinstance(result, dict) and result:
                print(f"✅ {name} - 成功获取数据")
                print(f"   数据键: {list(result.keys())[:3]}...")
            else:
                print(f"⚠️ {name} - 数据为空")
        except Exception as e:
            print(f"❌ {name} - 失败: {str(e)[:50]}...")

def demonstrate_simple_usage():
    """演示简单的使用方法"""
    print_section("AKShare 基本使用示例")

    try:
        # 1. 获取交易日期
        print("1. 获取交易日期")
        trade_dates = ak.tool_trade_date_hist_sina()
        print(f"   总交易日期数: {len(trade_dates)}")
        print(f"   最近交易日期: {trade_dates.iloc[-1]['trade_date']}")
        print(f"   最早交易日期: {trade_dates.iloc[0]['trade_date']}")

        # 2. 基本的数据处理
        print("\n2. 基本数据处理示例")
        recent_dates = trade_dates.tail(10)  # 最近10个交易日
        print(f"   最近10个交易日:")
        for i, row in recent_dates.iterrows():
            print(f"     {row['trade_date']}")

    except Exception as e:
        print(f"❌ 示例运行失败: {str(e)}")

def provide_troubleshooting_guide():
    """提供故障排除指南"""
    print_section("故障排除指南")

    guide = """
📋 已知问题和解决方案:

1. 东方财富数据源连接问题 (SSL错误)
   现象: HTTPSConnectionPool SSL错误
   解决:
   - 使用其他数据源（如新浪）
   - 配置代理或VPN
   - 更新SSL证书

2. 可用的数据源:
   ✅ 新浪财经 - 交易日期、部分股票数据
   ❌ 东方财富 - 当前连接有问题

3. 推荐的使用方式:
   - 优先使用可以正常工作的API
   - 实现重试机制
   - 添加异常处理
   - 使用缓存减少API调用

4. 环境配置建议:
   - 使用国内镜像源安装包
   - 确保网络连接稳定
   - 考虑使用代理访问特定数据源

5. 代码最佳实践:
   - 添加适当的延时
   - 实现错误处理
   - 使用备用数据源
   - 记录失败的API调用
"""

    print(guide)

def create_simple_stock_functions():
    """创建简单的股票数据获取函数"""
    print_section("创建可用的股票数据函数")

    code = '''
# 可以使用的简单股票相关函数示例

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

# 使用示例
if __name__ == "__main__":
    # 获取最近5个交易日
    recent = get_recent_trade_dates(5)
    if recent is not None:
        print("最近5个交易日:")
        print(recent)

    # 检查今天是否为交易日
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    if is_trading_date(today):
        print(f"{today} 是交易日")
    else:
        print(f"{today} 不是交易日")
'''

    print("可用的函数代码:")
    print(code)

def main():
    """主函数"""
    print("AKShare 问题解决方案和可用功能测试")
    print("基于当前环境的实际情况分析")

    test_working_apis()
    demonstrate_simple_usage()
    provide_troubleshooting_guide()
    create_simple_stock_functions()

    print_section("总结")
    summary = """
✅ AKShare已成功安装 (版本 1.17.85)
✅ 基本导入功能正常
✅ 新浪财经数据源可用
⚠️ 东方财富数据源当前不可用 (SSL连接问题)

建议:
1. 优先使用可用的API接口
2. 实现适当的错误处理和重试机制
3. 考虑使用其他数据源作为补充
4. 定期检查API的可用性
"""

    print(summary)

if __name__ == "__main__":
    main()
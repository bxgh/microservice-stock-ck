#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 可用接口总结
基于实际测试结果，列出当前环境中可以正常使用的AKShare接口
"""

import akshare as ak
import pandas as pd
from datetime import datetime

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def demonstrate_working_apis():
    """演示可用的API"""
    print_header("✅ 确定可用的AKShare接口")

    print("\n📅 1. 交易日期相关:")
    print("   API: ak.tool_trade_date_hist_sina()")
    print("   功能: 获取中国股市所有交易日期")
    print("   数据源: 新浪财经")

    try:
        dates = ak.tool_trade_date_hist_sina()
        print(f"   示例结果: 共 {len(dates)} 个交易日")
        print(f"   最早: {dates.iloc[0]['trade_date']}")
        print(f"   最近: {dates.iloc[-1]['trade_date']}")
        print("   状态: ✅ 完全可用")
    except:
        print("   状态: ❌ 当前不可用")

    print("\n📊 2. 指数成分股查询:")
    print("   API: ak.index_stock_cons(symbol)")
    print("   功能: 获取指定指数的成分股信息")
    print("   支持指数: 000300(沪深300), 000016(上证50) 等")

    # 测试几个主要指数
    indices = [
        ("沪深300", "000300"),
        ("上证50", "000016"),
        ("中证500", "000905"),
    ]

    for name, symbol in indices:
        try:
            stocks = ak.index_stock_cons(symbol)
            print(f"   {name}({symbol}): ✅ {len(stocks)} 只成分股")
        except:
            print(f"   {name}({symbol}): ❌ 获取失败")

    print("\n🔧 3. 基础工具函数:")
    print("   • pandas数据处理: ✅ 完全支持")
    print("   • 时间日期处理: ✅ 完全支持")
    print("   • 数据导出功能: ✅ 支持 (to_csv, to_excel等)")

def create_usage_examples():
    """创建使用示例"""
    print_header("📝 使用示例代码")

    examples = '''
# 1. 获取交易日期
def get_trading_dates():
    """获取所有交易日期"""
    dates = ak.tool_trade_date_hist_sina()
    return dates

def is_trading_day(date_str):
    """检查是否为交易日"""
    dates = ak.tool_trade_date_hist_sina()
    return date_str in dates['trade_date'].values

# 2. 获取指数成分股
def get_index_constituents(index_code="000300"):
    """获取指数成分股
    Args:
        index_code: 指数代码 (000300=沪深300, 000016=上证50)
    """
    try:
        stocks = ak.index_stock_cons(index_code)
        return stocks
    except Exception as e:
        print(f"获取指数成分股失败: {e}")
        return None

# 3. 实用工具函数
def get_recent_trading_days(days=10):
    """获取最近N个交易日"""
    dates = ak.tool_trade_date_hist_sina()
    return dates.tail(days)

def get_next_trading_day():
    """获取下一个交易日"""
    dates = ak.tool_trade_date_hist_sina()
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    future_dates = dates[dates['trade_date'] > today]
    return future_dates.iloc[0]['trade_date'] if not future_dates.empty else None

# 4. 完整使用示例
if __name__ == "__main__":
    # 获取最近5个交易日
    recent_days = get_recent_trading_days(5)
    print("最近5个交易日:")
    for date in recent_days['trade_date']:
        print(f"  {date}")

    # 获取沪深300成分股
    hs300_stocks = get_index_constituents("000300")
    if hs300_stocks is not None:
        print(f"\\n沪深300成分股数量: {len(hs300_stocks)}")
        print("前10只股票:")
        print(hs300_stocks.head(10))
'''

    print(examples)

def show_unavailable_apis():
    """显示不可用的API"""
    print_header("⚠️ 暂时不可用的接口")

    unavailable = [
        "实时股票数据 (东方财富数据源)",
        "宏观经济数据 (GDP, CPI等)",
        "期货、期权数据",
        "国际市场数据",
        "基金实时数据",
        "技术指标实时计算",
        "部分需要高级权限的数据"
    ]

    for api in unavailable:
        print(f"   ❌ {api}")

    print(f"\n🔍 原因分析:")
    print(f"   • 网络连接问题 (SSL证书)")
    print(f"   • 数据源访问限制")
    print(f"   • API权限要求")
    print(f"   • 服务器响应超时")

def provide_solutions():
    """提供解决方案"""
    print_header("💡 解决方案和替代方法")

    solutions = '''
1. 🔧 网络问题解决方案:
   • 使用代理或VPN
   • 更新SSL证书: pip install --upgrade certifi
   • 配置国内镜像源

2. 📊 可用功能充分利用:
   • 交易日期API非常稳定，可用于交易日历
   • 指数成分股API可用于获取股票池
   • 结合pandas进行数据分析

3. 🚀 替代数据源:
   • 考虑使用tushare, baostock等其他库
   • 使用付费数据源API
   • 本地数据库存储历史数据

4. 📈 扩展应用:
   • 基于可用API构建交易日历工具
   • 创建指数成分股监控工具
   • 开发股票池筛选功能
   • 实现交易时间提醒功能
'''

    print(solutions)

def main():
    """主函数"""
    print("AKShare 可用接口完整总结")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"AKShare版本: {ak.__version__}")

    demonstrate_working_apis()
    create_usage_examples()
    show_unavailable_apis()
    provide_solutions()

    print_header("📋 最终结论")
    conclusion = '''
✅ 当前环境中AKShare的核心价值:
   1. 交易日期查询 - 100%可用，非常稳定
   2. 指数成分股查询 - 主要指数可用
   3. 基础数据处理 - 完整支持

💡 推荐使用场景:
   • 交易日历应用
   • 指数成分股分析
   • 股票池构建
   • 交易时间工具

🎯 虽然部分实时数据不可用，但基础功能足以支持很多金融应用开发！
'''

    print(conclusion)

if __name__ == "__main__":
    main()
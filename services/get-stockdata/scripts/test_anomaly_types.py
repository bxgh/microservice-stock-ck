#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时脚本: 查询 akshare stock_changes_em 支持的所有异动类型

东方财富网盘口异动类型参考:
https://quote.eastmoney.com/changes/
"""

import akshare as ak

# 常见的盘口异动类型（根据东方财富网）
anomaly_types = [
    "火箭发射",    # 急速拉升
    "快速反弹",    # 快速反弹
    "大笔买入",    # 大单买入
    "封涨停板",    # 封住涨停
    "打开跌停板",  # 打开跌停
    "有大买盘",    # 大买盘堆积
    "有大卖盘",    # 大卖盘堆积
    "加速下跌",    # 快速下跌
    "高台跳水",    # 高位跳水
    "大笔卖出",    # 大单卖出
    "封跌停板",    # 封住跌停
    "打开涨停板",  # 打开涨停
    "竞价上涨",    # 集合竞价上涨
    "竞价下跌",    # 集合竞价下跌
    "触及涨停",    # 触及涨停（未封住）
    "触及跌停",    # 触及跌停（未封住）
    "盘中异动",    # 全部异动
]

print("=" * 60)
print("🔍 测试 akshare stock_changes_em 支持的异动类型")
print("=" * 60)

for anomaly_type in anomaly_types:
    try:
        df = ak.stock_changes_em(symbol=anomaly_type)
        if df is not None and len(df) > 0:
            print(f"✅ {anomaly_type:12s} - {len(df):4d} 条数据")
        else:
            print(f"⚠️ {anomaly_type:12s} - 空数据（可能非交易时段）")
    except Exception as e:
        print(f"❌ {anomaly_type:12s} - 错误: {str(e)[:50]}")

print("\n" + "=" * 60)
print("💡 建议: 根据测试结果选择有效的异动类型")
print("=" * 60)

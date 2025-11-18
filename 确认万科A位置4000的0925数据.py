#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
确认万科A位置4000的09:25数据
专门针对位置4000进行详细数据获取
"""

import sys
import os
import time
import pandas as pd
from datetime import datetime

sys.path.append('/home/bxgh/microservice-stock/services/get-stockdata/src')

def confirm_vanke_position_4000_data():
    """确认万科A位置4000的09:25数据"""

    print("=" * 80)
    print("🎯 确认万科A位置4000的09:25数据")
    print("=" * 80)
    print(f"股票代码: 000002 万科A")
    print(f"目标日期: 2025-11-18")
    print(f"探测发现: 位置4000有09:25数据")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    from mootdx.quotes import Quotes

    client = Quotes.factory(
        market='std',
        multithread=True,
        heartbeat=True,
        bestip=False,
        timeout=30
    )

    try:
        symbol = '000002'
        date = '20251118'

        # 专门获取位置4000的数据
        print(f"\n🔍 专门获取位置4000的数据...")

        start_pos = 4000
        test_offsets = [100, 200, 300, 400, 500, 600, 800, 1000]

        for offset in test_offsets:
            print(f"\n📋 测试: start={start_pos}, offset={offset}")

            try:
                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=offset
                )

                if batch_data is not None and not batch_data.empty:
                    earliest_time = batch_data['time'].iloc[0]
                    latest_time = batch_data['time'].iloc[-1]
                    record_count = len(batch_data)

                    print(f"   ✅ {record_count}条记录")
                    print(f"   🕐 时间范围: {earliest_time} - {latest_time}")

                    # 详细分析时间分布
                    time_counts = batch_data['time'].value_counts().sort_index()
                    print(f"   📊 时间分布:")
                    for time_val, count in time_counts.head(10).items():
                        print(f"      {time_val}: {count}条")

                    # 检查09:25数据
                    data_0925 = batch_data[batch_data['time'] == '09:25']
                    if not data_0925.empty:
                        print(f"   🏅 找到09:25数据! {len(data_0925)}条记录")
                        print(f"   📋 09:25详细数据:")
                        print(data_0925.to_string(index=False))

                        # 保存包含09:25的完整数据
                        filename = f"万科A_位置4000_offset{offset}_包含0925.csv"
                        batch_data.to_csv(filename, index=False, encoding='utf-8-sig')
                        print(f"   💾 数据保存: {filename}")

                        # 分析09:25数据的买卖方向
                        buy_count = len(data_0925[data_0925['buyorsell'] == 1])
                        sell_count = len(data_0925[data_0925['buyorsell'] == 2])
                        neutral_count = len(data_0925[data_0925['buyorsell'] == 0])

                        print(f"   📊 09:25买卖分析:")
                        print(f"      买入: {buy_count}笔")
                        print(f"      卖出: {sell_count}笔")
                        print(f"      中性: {neutral_count}笔")

                        return True

                    # 检查09:30数据
                    data_0930 = batch_data[batch_data['time'] == '09:30']
                    if not data_0930.empty:
                        print(f"   ✅ 找到09:30数据: {len(data_0930)}条记录")
                        if len(data_0930) <= 5:
                            print(f"   📋 09:30详细数据:")
                            print(data_0930.to_string(index=False))

                    # 显示最早几条数据
                    print(f"   📋 最早5条记录:")
                    print(batch_data.head()[['time', 'price', 'vol', 'buyorsell']].to_string(index=False))

                else:
                    print(f"   ❌ 无数据")

                time.sleep(0.2)

            except Exception as e:
                print(f"   ❌ 获取失败: {e}")
                continue

        # 扩大搜索范围：位置3900-4100
        print(f"\n🔍 扩大搜索范围: 位置3900-4100")

        for start_pos in range(3900, 4101, 50):
            try:
                print(f"   📋 测试位置: {start_pos}")

                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=500
                )

                if batch_data is not None and not batch_data.empty:
                    earliest_time = batch_data['time'].iloc[0]

                    if earliest_time <= "09:25":
                        print(f"      🏅 位置{start_pos}: {earliest_time} - 找到09:25数据!")

                        # 检查09:25数据
                        data_0925 = batch_data[batch_data['time'] == '09:25']
                        if not data_0925.empty:
                            print(f"      📋 09:25记录数: {len(data_0925)}")

                            filename = f"万科A_位置{start_pos}_找到0925.csv"
                            data_0925.to_csv(filename, index=False, encoding='utf-8-sig')
                            print(f"      💾 09:25数据保存: {filename}")

                    elif earliest_time <= "09:30":
                        print(f"      ✅ 位置{start_pos}: {earliest_time}")

                else:
                    print(f"      ❌ 位置{start_pos}: 无数据")

                time.sleep(0.1)

            except Exception as e:
                continue

        return False

    finally:
        client.close()


def get_vanke_0925_data_from_position_4000():
    """从位置4000开始，逐步向前搜索09:25数据"""

    print(f"\n🔍 从位置4000开始逐步向前搜索09:25数据")

    from mootdx.quotes import Quotes

    client = Quotes.factory(
        market='std',
        multithread=True,
        heartbeat=True,
        bestip=False,
        timeout=30
    )

    try:
        symbol = '000002'
        date = '20251118'

        # 从4000开始，逐步减小start值，增加offset值
        search_configs = [
            (4000, 200), (3800, 300), (3600, 400), (3400, 500), (3200, 600),
            (3000, 800), (2800, 1000), (2600, 1200), (2400, 1500), (2200, 2000),
            (2000, 2500), (1800, 3000), (1600, 4000), (1400, 5000)
        ]

        for start_pos, offset in search_configs:
            try:
                print(f"   📋 搜索: start={start_pos}, offset={offset}")

                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=offset
                )

                if batch_data is not None and not batch_data.empty:
                    earliest_time = batch_data['time'].iloc[0]
                    latest_time = batch_data['time'].iloc[-1]
                    record_count = len(batch_data)

                    print(f"      ✅ {record_count}条 {earliest_time}-{latest_time}")

                    if earliest_time <= "09:25":
                        print(f"      🏅 找到09:25数据!")

                        data_0925 = batch_data[batch_data['time'] == '09:25']
                        if not data_0925.empty:
                            print(f"      📋 09:25记录: {len(data_0925)}条")
                            print(f"      📋 09:25数据:")
                            print(data_0925.to_string(index=False))

                            filename = f"万科A_0925数据_start{start_pos}_offset{offset}.csv"
                            batch_data.to_csv(filename, index=False, encoding='utf-8-sig')
                            print(f"      💾 完整数据保存: {filename}")

                        return True

                    elif earliest_time <= "09:30":
                        print(f"      ✅ 找到09:30数据")

                else:
                    print(f"      ❌ 无数据")

                time.sleep(0.1)

            except Exception as e:
                print(f"      ❌ 搜索失败: {e}")
                continue

        return False

    finally:
        client.close()


if __name__ == "__main__":
    print("开始确认万科A位置4000的09:25数据...")

    # 方法1：确认位置4000的数据
    success1 = confirm_vanke_position_4000_data()

    if not success1:
        # 方法2：从位置4000开始向前搜索
        success2 = get_vanke_0925_data_from_position_4000()

        if success2:
            print(f"\n🎉 成功获取万科A 09:25数据!")
        else:
            print(f"\n❌ 确认万科A确实没有09:25集合竞价数据")
    else:
        print(f"\n🎉 成功获取万科A 09:25数据!")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取万科A 09:25分笔数据的专门策略
使用多种方法和深度搜索，确保获取到09:25集合竞价数据
"""

import sys
import os
import time
import pandas as pd
from datetime import datetime

sys.path.append('/home/bxgh/microservice-stock/services/get-stockdata/src')

def get_vanke_0925_data_specialized():
    """专门获取万科A 09:25分笔数据"""

    print("=" * 80)
    print("🎯 专门获取万科A 09:25分笔数据")
    print("=" * 80)
    print(f"股票代码: 000002 万科A")
    print(f"目标日期: 2025-11-18")
    print(f"核心目标: 必须获取到09:25集合竞价数据")
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

        # 方法1: 极深位置搜索 (重点尝试更深的start位置)
        print("\n🔍 方法1: 极深位置搜索 (寻找09:25数据)")
        ultra_deep_positions = [
            25000, 28000, 30000, 32000, 35000, 38000, 40000, 42000,
            45000, 48000, 50000, 55000, 60000, 65000, 70000, 75000, 80000
        ]

        found_0925_data = None

        for start_pos in ultra_deep_positions:
            try:
                print(f"   🔍 深度探测: start={start_pos}")

                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=1000  # 更大的批次
                )

                if batch_data is not None and not batch_data.empty:
                    earliest_time = batch_data['time'].iloc[0]
                    latest_time = batch_data['time'].iloc[-1]
                    record_count = len(batch_data)

                    print(f"      ✅ {record_count}条 {earliest_time}-{latest_time}")

                    # 检查是否包含09:25数据
                    if earliest_time <= "09:25":
                        print(f"      🏅 找到09:25数据！")
                        found_0925_data = batch_data

                        # 保存这批数据
                        filename = f"万科A_0925数据_start{start_pos}.csv"
                        batch_data.to_csv(filename, index=False, encoding='utf-8-sig')
                        print(f"      💾 09:25数据保存: {filename}")

                        break
                    elif earliest_time <= "09:30":
                        print(f"      ✅ 找到09:30数据")

                        # 检查数据中是否包含09:25
                        has_0925 = not batch_data[batch_data['time'] == '09:25'].empty
                        if has_0925:
                            print(f"      🏅 在09:30数据中发现09:25记录！")
                            found_0925_data = batch_data[batch_data['time'] == '09:25']
                            break

                else:
                    print(f"      ❌ 无数据")

                time.sleep(0.2)

            except Exception as e:
                print(f"      ❌ 探测失败: {e}")
                continue

        # 方法2: 多批次小范围搜索
        if found_0925_data is None:
            print("\n🔍 方法2: 多批次小范围搜索")

            # 基于之前找到的位置进行精细搜索
            base_positions = [20000, 22000, 24000, 26000, 28000, 30000, 32000]

            for base_pos in base_positions:
                print(f"   🔍 基础位置 {base_pos} 周边搜索...")

                # 在基础位置前后搜索
                for offset in range(-1000, 2000, 200):  # -1000 到 +2000，步进200
                    search_pos = base_pos + offset
                    if search_pos <= 0:
                        continue

                    try:
                        batch_data = client.transactions(
                            symbol=symbol, date=date,
                            start=search_pos, offset=500
                        )

                        if batch_data is not None and not batch_data.empty:
                            earliest_time = batch_data['time'].iloc[0]

                            if earliest_time <= "09:25":
                                print(f"      🏅 位置{search_pos}: 找到09:25数据! {earliest_time}")
                                found_0925_data = batch_data
                                break
                            elif earliest_time <= "09:30":
                                has_0925 = not batch_data[batch_data['time'] == '09:25'].empty
                                if has_0925:
                                    print(f"      🏅 位置{search_pos}: 发现09:25记录! {earliest_time}")
                                    found_0925_data = batch_data[batch_data['time'] == '09:25']
                                    break

                    except Exception as e:
                        continue

                time.sleep(0.1)

                if found_0925_data is not None:
                    break

        # 方法3: 不同的offset参数测试
        if found_0925_data is None:
            print("\n🔍 方法3: 不同offset参数测试")

            test_positions = [35000, 40000, 45000, 50000, 55000]
            test_offsets = [500, 800, 1000, 1200, 1500, 2000, 3000]

            for start_pos in test_positions:
                print(f"   🔍 位置{start_pos} 不同offset测试...")

                for offset in test_offsets:
                    try:
                        batch_data = client.transactions(
                            symbol=symbol, date=date,
                            start=start_pos, offset=offset
                        )

                        if batch_data is not None and not batch_data.empty:
                            earliest_time = batch_data['time'].iloc[0]

                            if earliest_time <= "09:25":
                                print(f"      🏅 start={start_pos}, offset={offset}: 找到09:25数据!")
                                found_0925_data = batch_data
                                break
                            elif earliest_time <= "09:30":
                                has_0925 = not batch_data[batch_data['time'] == '09:25'].empty
                                if has_0925:
                                    print(f"      🏅 start={start_pos}, offset={offset}: 发现09:25记录!")
                                    found_0925_data = batch_data[batch_data['time'] == '09:25']
                                    break

                    except Exception as e:
                        continue

                    time.sleep(0.05)

                if found_0925_data is not None:
                    break

        # 方法4: 尝试实时交易方法
        if found_0925_data is None:
            print("\n🔍 方法4: 尝试实时交易方法 (无date参数)")

            try:
                realtime_data = client.transaction(symbol=symbol, start=0, offset=5000)

                if realtime_data is not None and not realtime_data.empty:
                    print(f"   ✅ 实时数据获取成功: {len(realtime_data)}条")
                    print(f"   🕐 时间范围: {realtime_data['time'].iloc[0]} - {realtime_data['time'].iloc[-1]}")

                    # 检查是否包含09:25数据
                    has_0925 = not realtime_data[realtime_data['time'] == '09:25'].empty
                    if has_0925:
                        print(f"   🏅 在实时数据中发现09:25数据!")
                        found_0925_data = realtime_data[realtime_data['time'] == '09:25']
                    else:
                        print(f"   ❌ 实时数据中未找到09:25数据")

                        # 显示最早的数据时间
                        earliest_rt = realtime_data['time'].iloc[0]
                        print(f"   📊 实时数据最早时间: {earliest_rt}")

            except Exception as e:
                print(f"   ❌ 实时数据获取失败: {e}")

        # 方法5: 基于已知成功位置的搜索
        if found_0925_data is None:
            print("\n🔍 方法5: 基于已知成功位置的搜索")

            # 基于我们之前测试中成功获取到09:25数据的股票位置模式
            # 银行股通常在4000-6000位置，尝试类似位置
            proven_positions = [4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000]

            for pos in proven_positions:
                try:
                    # 尝试不同的批次大小
                    for batch_size in [300, 400, 500, 600, 800, 1000]:
                        batch_data = client.transactions(
                            symbol=symbol, date=date,
                            start=pos, offset=batch_size
                        )

                        if batch_data is not None and not batch_data.empty:
                            earliest_time = batch_data['time'].iloc[0]

                            if earliest_time <= "09:25":
                                print(f"      🏅 位置{pos}, 批次{batch_size}: 找到09:25数据!")
                                found_0925_data = batch_data
                                break
                            elif earliest_time <= "09:30":
                                has_0925 = not batch_data[batch_data['time'] == '09:25'].empty
                                if has_0925:
                                    print(f"      🏅 位置{pos}, 批次{batch_size}: 发现09:25记录!")
                                    found_0925_data = batch_data[batch_data['time'] == '09:25']
                                    break

                    if found_0925_data is not None:
                        break

                    time.sleep(0.1)

                except Exception as e:
                    continue

        # 最终结果分析
        print(f"\n" + "="*60)
        print(f"📊 万科A 09:25数据获取结果")
        print(f"="*60)

        if found_0925_data is not None and not found_0925_data.empty:
            print(f"🎉 成功获取万科A 09:25数据!")
            print(f"📊 记录数: {len(found_0925_data)}条")
            print(f"🕐 时间: {found_0925_data['time'].iloc[0]}")
            print(f"💰 价格: {found_0925_data['price'].iloc[0]:.2f}")
            print(f"📈 成交量: {found_0925_data['vol'].iloc[0]}手")

            # 显示详细数据
            print(f"\n📋 09:25详细分笔数据:")
            print(found_0925_data.to_string(index=False))

            # 保存数据
            filename = "万科A_0925成功获取.csv"
            found_0925_data.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 09:25数据已保存: {filename}")

        else:
            print(f"❌ 未能获取到万科A 09:25数据")

            # 显示我们找到的最早时间
            earliest_found_time = None
            print(f"\n📋 我们找到的最早时间记录:")

            # 重新搜索一次，只记录最早时间
            for start_pos in [0, 2000, 4000, 6000, 8000, 10000, 20000, 30000, 40000, 50000]:
                try:
                    sample_data = client.transactions(
                        symbol=symbol, date=date,
                        start=start_pos, offset=500
                    )

                    if sample_data is not None and not sample_data.empty:
                        current_earliest = sample_data['time'].iloc[0]

                        if earliest_found_time is None or current_earliest < earliest_found_time:
                            earliest_found_time = current_earliest
                            print(f"   📊 位置{start_pos}: 最早时间 {current_earliest}")

                except:
                    continue

            print(f"\n📈 最终最早时间: {earliest_found_time if earliest_found_time else '无数据'}")
            print(f"💡 可能原因:")
            print(f"   1. 该股票在该日期确实没有09:25集合竞价数据")
            print(f"   2. 数据源不保存集合竞价数据")
            print(f"   3. 需要使用其他API或数据源")

    finally:
        client.close()


def test_different_date_for_vanke():
    """测试万科A不同日期的09:25数据获取"""

    print(f"\n🔄 测试万科A不同日期的09:25数据获取")
    print(f"="*50)

    test_dates = ['20251114', '20251113', '20251112']  # 测试前几个交易日

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

        for test_date in test_dates:
            print(f"\n📅 测试日期: {test_date}")

            found_0925 = False

            # 使用成功案例中的策略
            test_positions = [4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000]

            for start_pos in test_positions:
                try:
                    batch_data = client.transactions(
                        symbol=symbol, date=test_date,
                        start=start_pos, offset=600
                    )

                    if batch_data is not None and not batch_data.empty:
                        earliest_time = batch_data['time'].iloc[0]

                        if earliest_time <= "09:25":
                            print(f"   🏅 {test_date} 在位置{start_pos}找到09:25数据! {earliest_time}")
                            found_0925 = True
                            break
                        elif earliest_time <= "09:30":
                            print(f"   ✅ {test_date} 在位置{start_pos}找到09:30数据 {earliest_time}")

                except Exception as e:
                    continue

            if not found_0925:
                print(f"   ❌ {test_date} 未找到09:25数据")

    finally:
        client.close()


if __name__ == "__main__":
    # 专门获取万科A 09:25数据
    get_vanke_0925_data_specialized()

    # 测试不同日期
    test_different_date_for_vanke()
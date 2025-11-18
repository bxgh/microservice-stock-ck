#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单独获取000002万科A 2025-11-18完整分笔数据
专门针对万科A在2025-11-18的数据进行深度获取和分析
"""

import sys
import os
import time
import pandas as pd
from datetime import datetime

sys.path.append('/home/bxgh/microservice-stock/services/get-stockdata/src')

def get_000002_complete_20251118_data():
    """获取000002万科A 2025-11-18完整分笔数据"""

    print("=" * 80)
    print("🏢 单独获取000002万科A 2025-11-18完整分笔数据")
    print("=" * 80)
    print(f"股票代码: 000002")
    print(f"股票名称: 万科A")
    print(f"目标日期: 2025-11-18")
    print(f"获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    from mootdx.quotes import Quotes

    # 创建客户端
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

        print("🚀 开始获取万科A完整分笔数据...")
        print("🎯 目标：获取从最早时间到收盘的完整数据")
        print()

        # 扩展搜索策略，确保获取最完整的数据
        all_data = []

        # 策略1：精细搜索（覆盖0-5000位置）
        fine_search_positions = [0, 200, 400, 600, 800, 1000, 1200, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]
        print(f"📋 步骤1: 精细搜索 {len(fine_search_positions)} 个位置...")

        for i, start_pos in enumerate(fine_search_positions):
            try:
                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=400
                )

                if batch_data is not None and not batch_data.empty:
                    earliest_time = batch_data['time'].iloc[0]
                    latest_time = batch_data['time'].iloc[-1]
                    record_count = len(batch_data)

                    print(f"   ✅ 位置{start_pos:4d}: {record_count:4d}条 {earliest_time}-{latest_time}")

                    all_data.append(batch_data)

                    # 如果找到了09:25数据，可以记录
                    if earliest_time <= "09:25":
                        print(f"      🏅 发现09:25数据！")
                    elif earliest_time <= "09:30":
                        print(f"      ✅ 发现09:30数据")
                    elif earliest_time <= "09:45":
                        print(f"      📋 发现09:45数据")

                else:
                    print(f"   ❌ 位置{start_pos:4d}: 无数据")

                time.sleep(0.1)

            except Exception as e:
                print(f"   ❌ 位置{start_pos:4d}: 获取失败 - {e}")
                continue

        # 策略2：深度搜索（寻找更早的数据）
        if all_data:
            current_earliest = min([data['time'].iloc[0] for data in all_data])
            print(f"\n📋 当前最早时间: {current_earliest}")

            if current_earliest > "09:30":
                print(f"🔍 需要深度搜索寻找更早数据...")

                # 深度搜索位置
                deep_search_positions = [6000, 7000, 8000, 9000, 10000, 12000, 15000, 18000, 20000]
                found_earlier = False

                for start_pos in deep_search_positions:
                    try:
                        print(f"   🔍 深度探测位置: {start_pos}")

                        batch_data = client.transactions(
                            symbol=symbol, date=date,
                            start=start_pos, offset=600
                        )

                        if batch_data is not None and not batch_data.empty:
                            earliest_time = batch_data['time'].iloc[0]
                            latest_time = batch_data['time'].iloc[-1]
                            record_count = len(batch_data)

                            print(f"      ✅ 深度数据: {record_count}条 {earliest_time}-{latest_time}")

                            # 检查是否找到了更早的数据
                            if earliest_time < current_earliest:
                                current_earliest = earliest_time
                                found_earlier = True
                                print(f"      🎯 发现更早数据！新最早时间: {earliest_time}")
                                all_data.append(batch_data)

                                # 如果找到了09:25数据，可以停止
                                if earliest_time <= "09:25":
                                    print(f"      🏅 找到09:25数据，停止深度搜索")
                                    break

                        else:
                            print(f"      ❌ 位置{start_pos}: 无数据")

                        time.sleep(0.2)

                    except Exception as e:
                        print(f"      ❌ 位置{start_pos}: 深度探测失败 - {e}")
                        continue

                if not found_earlier:
                    print(f"   ⚠️ 深度搜索未找到更早数据")

        # 策略3：实时数据补充
        print(f"\n📋 步骤3: 获取实时数据补充...")
        try:
            realtime_data = client.transaction(symbol=symbol, start=0, offset=2000)
            if realtime_data is not None and not realtime_data.empty:
                rt_earliest = realtime_data['time'].iloc[0]
                rt_latest = realtime_data['time'].iloc[-1]
                rt_count = len(realtime_data)

                print(f"   ✅ 实时数据: {rt_count}条 {rt_earliest}-{rt_latest}")

                # 检查实时数据是否包含新的时间
                if all_data:
                    existing_times = set()
                    for data in all_data:
                        existing_times.update(data['time'].tolist())

                    new_times = set(realtime_data['time'])
                    new_data_count = len(new_times - existing_times)

                    if new_data_count > 0:
                        print(f"   📊 实时数据包含 {new_data_count} 个新时间点")
                        all_data.append(realtime_data)
                    else:
                        print(f"   📊 实时数据时间点已存在")
                else:
                    all_data.append(realtime_data)

        except Exception as e:
            print(f"   ❌ 实时数据获取失败: {e}")

        # 数据整合和处理
        if all_data:
            print(f"\n🔄 数据整合和处理...")

            # 合并所有数据
            merged_data = pd.concat(all_data, ignore_index=True)
            original_count = len(merged_data)

            # 多维度去重
            merged_data = merged_data.drop_duplicates(subset=['time', 'price', 'vol'])
            after_dedup_count = len(merged_data)

            # 按时间排序
            merged_data = merged_data.sort_values('time').reset_index(drop=True)

            # 添加增强字段
            merged_data['symbol'] = symbol
            merged_data['date'] = date
            merged_data['name'] = '万科A'
            merged_data['category'] = '地产股'

            # 计算累计成交量
            if 'vol' in merged_data.columns:
                merged_data['cumulative_volume'] = merged_data['vol'].cumsum()

            # 添加买卖方向统计
            buy_sell_stats = merged_data['buyorsell'].value_counts()
            buy_count = buy_sell_stats.get(1, 0)
            sell_count = buy_sell_stats.get(2, 0)
            neutral_count = buy_sell_stats.get(0, 0)

            # 时间分析
            earliest_time = merged_data['time'].iloc[0]
            latest_time = merged_data['time'].iloc[-1]

            # 检查关键时间点
            has_0925 = not merged_data[merged_data['time'] == '09:25'].empty
            has_0930 = not merged_data[merged_data['time'] == '09:30'].empty
            has_0945 = not merged_data[merged_data['time'] == '09:45'].empty

            # 打印详细分析
            print(f"\n📊 万科A 2025-11-18 分笔数据分析报告:")
            print(f"=" * 60)
            print(f"📈 数据统计:")
            print(f"   原始记录数: {original_count:,}")
            print(f"   去重后记录: {after_dedup_count:,}")
            print(f"   去重率: {((original_count - after_dedup_count) / original_count * 100):.1f}%")
            print(f"   🕐 时间范围: {earliest_time} - {latest_time}")
            print(f"   💰 价格范围: {merged_data['price'].min():.2f} - {merged_data['price'].max():.2f}")

            print(f"\n🏅 关键时间点覆盖:")
            print(f"   09:25数据: {'✅ 有' if has_0925 else '❌ 无'}")
            print(f"   09:30数据: {'✅ 有' if has_0930 else '❌ 无'}")
            print(f"   09:45数据: {'✅ 有' if has_0945 else '❌ 无'}")

            print(f"\n📊 交易统计:")
            print(f"   买入订单: {buy_count:,}笔 ({(buy_count/after_dedup_count*100):.1f}%)")
            print(f"   卖出订单: {sell_count:,}笔 ({(sell_count/after_dedup_count*100):.1f}%)")
            print(f"   中性订单: {neutral_count:,}笔 ({(neutral_count/after_dedup_count*100):.1f}%)")

            # 时间段分析
            print(f"\n📅 时间段覆盖分析:")
            time_segments = [
                ('开盘前集合竞价', '09:15', '09:30'),
                ('上午开盘', '09:30', '10:00'),
                ('上午中段', '10:00', '11:00'),
                ('上午收盘', '11:00', '11:30'),
                ('下午开盘', '13:00', '14:00'),
                ('下午中段', '14:00', '15:00'),
            ]

            covered_segments = 0
            total_volume = 0

            for segment_name, start_time, end_time in time_segments:
                segment_data = merged_data[
                    (merged_data['time'] >= start_time) &
                    (merged_data['time'] < end_time)
                ]

                if not segment_data.empty:
                    covered_segments += 1
                    count = len(segment_data)
                    volume = segment_data['vol'].sum() if 'vol' in segment_data.columns else 0
                    total_volume += volume

                    print(f"   ✅ {segment_name} ({start_time}-{end_time}): {count:4d}条, {volume:8,}手")
                else:
                    print(f"   ❌ {segment_name} ({start_time}-{end_time}): 无数据")

            coverage_rate = covered_segments / len(time_segments) * 100
            print(f"\n📊 时段覆盖率: {coverage_rate:.1f}% ({covered_segments}/{len(time_segments)})")
            print(f"📊 总成交量: {total_volume:,}手")

            # 保存完整数据
            filename = f"万科A_000002_20251118_完整分笔数据.csv"
            merged_data.to_csv(filename, index=False, encoding='utf-8-sig')
            file_size = os.path.getsize(filename) / 1024  # KB
            print(f"\n💾 完整数据已保存: {filename} ({file_size:.1f} KB)")

            # 显示数据样本
            print(f"\n📋 数据样本 (前10条):")
            print(merged_data[['time', 'price', 'vol', 'buyorsell', 'cumulative_volume']].head(10).to_string(index=False))

            print(f"\n📋 数据样本 (后10条):")
            print(merged_data[['time', 'price', 'vol', 'buyorsell', 'cumulative_volume']].tail(10).to_string(index=False))

            # 检查具体的09:25和09:30数据
            if has_0925:
                data_0925 = merged_data[merged_data['time'] == '09:25']
                print(f"\n🏅 09:25详细数据:")
                print(data_0925[['time', 'price', 'vol', 'buyorsell', 'cumulative_volume']].to_string(index=False))

            if has_0930:
                data_0930 = merged_data[merged_data['time'] == '09:30']
                print(f"\n📈 09:30详细数据:")
                print(f"   总记录数: {len(data_0930)}条")
                print(data_0930[['time', 'price', 'vol', 'buyorsell']].head(5).to_string(index=False))
                if len(data_0930) > 5:
                    print("   ...")
                    print(data_0930[['time', 'price', 'vol', 'buyorsell']].tail(3).to_string(index=False))

            return merged_data

        else:
            print(f"\n❌ 未能获取到万科A 2025-11-18的分笔数据")
            return pd.DataFrame()

    finally:
        client.close()


def analyze_000002_special_features(data: pd.DataFrame):
    """分析万科A的特殊特征"""

    if data.empty:
        print(f"\n❌ 无数据可分析")
        return

    print(f"\n🏢 万科A (000002) 特征分析:")
    print(f"=" * 50)

    # 价格波动分析
    price_change = data['price'].max() - data['price'].min()
    price_change_rate = (price_change / data['price'].min()) * 100

    print(f"💰 价格波动分析:")
    print(f"   最高价: {data['price'].max():.2f}")
    print(f"   最低价: {data['price'].min():.2f}")
    print(f"   波动幅度: {price_change:.2f} ({price_change_rate:.2f}%)")

    # 成交活跃度分析
    if len(data) > 1:
        # 计算每分钟的成交量
        data['time_obj'] = pd.to_datetime(data['time'], format='%H:%M')
        data['minute'] = data['time_obj'].dt.hour * 60 + data['time_obj'].dt.minute
        minute_volume = data.groupby('minute')['vol'].sum()

        avg_minute_volume = minute_volume.mean()
        max_minute_volume = minute_volume.max()

        print(f"\n📊 成交活跃度分析:")
        print(f"   平均每分钟成交量: {avg_minute_volume:.0f}手")
        print(f"   最高每分钟成交量: {max_minute_volume:.0f}手")
        print(f"   总交易记录数: {len(data):,}条")

    # 买卖力量分析
    buy_data = data[data['buyorsell'] == 1]
    sell_data = data[data['buyorsell'] == 2]

    buy_volume = buy_data['vol'].sum() if not buy_data.empty else 0
    sell_volume = sell_data['vol'].sum() if not sell_data.empty else 0

    print(f"\n⚖️ 买卖力量对比:")
    print(f"   买入成交量: {buy_volume:,}手")
    print(f"   卖出成交量: {sell_volume:,}手")
    print(f"   净买入: {buy_volume - sell_volume:,}手")

    if sell_volume > 0:
        buy_sell_ratio = buy_volume / sell_volume
        print(f"   买卖比: {buy_sell_ratio:.2f}")

        if buy_sell_ratio > 1.2:
            print(f"   📈 市场情绪: 强烈看涨")
        elif buy_sell_ratio > 1.0:
            print(f"   📊 市场情绪: 温和看涨")
        elif buy_sell_ratio > 0.8:
            print(f"   📉 市场情绪: 温和看跌")
        else:
            print(f"   🔻 市场情绪: 强烈看跌")


if __name__ == "__main__":
    # 获取万科A完整数据
    vanke_data = get_000002_complete_20251118_data()

    # 分析万科A特征
    analyze_000002_special_features(vanke_data)
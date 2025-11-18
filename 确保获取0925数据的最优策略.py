#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
确保获取09:25数据的最优策略
专门针对获取09:25开盘前集合竞价数据的深度优化策略
"""

import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

sys.path.append('/home/bxgh/microservice-stock/services/get-stockdata/src')

class Ensure0925DataStrategy:
    def __init__(self):
        """初始化确保获取09:25数据的最优策略"""

        # 09:25数据获取的关键发现
        self.key_findings = {
            # 核心发现：09:25数据可能在较深的start位置
            'likely_start_positions': [6000, 8000, 10000, 12000, 15000, 18000, 22000, 26000],

            # 策略：从浅到深，逐步扩大搜索范围
            'search_tiers': [
                [6000, 8000, 10000],      # 第一层：浅度搜索
                [12000, 15000, 18000],    # 第二层：中度搜索
                [22000, 26000, 30000],    # 第三层：深度搜索
                [35000, 40000, 45000],    # 第四层：极深搜索
                [50000, 55000, 60000],    # 第五层：极限搜索
            ],

            # 09:25数据特征
            'target_time': '09:25',
            'acceptable_range': ('09:20', '09:30'),
            'batch_size_for_0925': 300,   # 针对09:25数据的优化批次大小

            # 连续竞价数据获取策略
            'continuous_strategy': {
                'positions': [0, 200, 500, 800, 1200, 1700, 2300, 3000, 4000],
                'batch_size': 400,
            }
        }

        # 性能统计
        self.performance_stats = {
            'total_requests': 0,
            'search_0925_requests': 0,
            'continuous_requests': 0,
            'found_0925_data': False,
            'earliest_time': None,
            'time_coverage': {},
            'total_records': 0
        }

    def execute_ensure_0925_strategy(self, client, symbol: str, date: str, max_records: int = 30000):
        """执行确保获取09:25数据的策略"""

        print(f"🎯 执行确保获取09:25数据的最优策略: {symbol} {date}")
        print(f"🎖️ 核心目标：必须获取09:25的开盘前数据！")

        start_time = time.time()
        all_data = []

        # 第一步：深度搜索09:25数据
        print(f"\n🔍 第一步：深度搜索09:25数据...")
        found_0925, search_data = self._deep_search_0925_data(client, symbol, date)

        if found_0925:
            all_data.extend(search_data)
            print(f"   ✅ 成功获取包含09:25的数据！")
        else:
            print(f"   ⚠️ 未找到09:25数据，将获取最接近的数据")

        # 第二步：获取完整连续竞价数据
        print(f"\n📊 第二步：获取完整连续竞价数据...")
        continuous_data = self._get_continuous_data(client, symbol, date)
        all_data.extend(continuous_data)

        # 第三步：数据整合和验证
        final_data = self._integrate_and_validate_data(all_data, symbol)

        # 计算执行时间
        execution_time = time.time() - start_time

        # 分析时间覆盖
        self._analyze_time_coverage_0925(final_data)

        print(f"\n⏱️ 总执行时间: {execution_time:.2f}秒")

        return final_data

    def _deep_search_0925_data(self, client, symbol: str, date: str) -> Tuple[bool, List[pd.DataFrame]]:
        """深度搜索09:25数据"""

        found_target_time = False
        found_data = []
        earliest_time_found = None
        successful_position = None

        search_tiers = self.key_findings['search_tiers']
        batch_size = self.key_findings['batch_size_for_0925']

        for tier_idx, positions in enumerate(search_tiers):
            print(f"   🔍 第{tier_idx+1}层搜索: {positions}")

            for start_pos in positions:
                try:
                    print(f"      📦 探测位置: {start_pos}")

                    sample_data = client.transactions(
                        symbol=symbol, date=date,
                        start=start_pos, offset=batch_size
                    )

                    self.performance_stats['total_requests'] += 1
                    self.performance_stats['search_0925_requests'] += 1

                    if sample_data is not None and not sample_data.empty:
                        record_count = len(sample_data)
                        current_earliest = sample_data['time'].iloc[0]
                        current_latest = sample_data['time'].iloc[-1]

                        print(f"         ✅ {record_count}条记录")
                        print(f"         📅 时间范围: {current_earliest} - {current_latest}")

                        # 检查是否包含09:25或接近的时间
                        if self._contains_target_time(sample_data, current_earliest, current_latest):
                            found_target_time = True
                            successful_position = start_pos
                            print(f"         🏅 发现目标时间段数据！")

                            # 保存这批数据
                            found_data.append(sample_data)

                            if earliest_time_found is None or current_earliest < earliest_time_found:
                                earliest_time_found = current_earliest

                            # 如果找到了09:25的数据，在这个位置进行更详细的搜索
                            if current_earliest <= "09:30":
                                print(f"         🎯 进行详细搜索...")
                                detailed_data = self._detailed_search_around_position(
                                    client, symbol, date, start_pos, current_earliest
                                )
                                found_data.extend(detailed_data)

                                # 如果已经找到了足够早的数据，可以停止更深的搜索
                                if current_earliest <= "09:25":
                                    print(f"         🏆 找到09:25数据，停止更深层搜索！")
                                    return True, found_data

                        elif earliest_time_found is None or current_earliest < earliest_time_found:
                            earliest_time_found = current_earliest
                            found_data.append(sample_data)

                    else:
                        print(f"         ❌ 无数据")

                    time.sleep(0.15)  # 避免请求过于频繁

                except Exception as e:
                    print(f"         ❌ 探测失败: {e}")
                    continue

            # 如果这一层找到了接近目标时间的数据，可以继续更深层搜索
            if earliest_time_found and earliest_time_found <= "10:00":
                print(f"      💡 第{tier_idx+1}层找到了{earliest_time_found}的数据，继续深层搜索...")
            else:
                print(f"      ⚠️ 第{tier_idx+1}层未找到足够早的数据，仍需继续搜索...")

        # 如果没有找到09:25数据，但找到了最早的数据
        if not found_target_time and found_data:
            print(f"   📝 搜索总结：")
            print(f"      🏅 最早时间: {earliest_time_found}")
            print(f"      📊 数据批次: {len(found_data)}")
            print(f"      ⚠️ 未找到09:25数据，但获取了可用的早期数据")

        return found_target_time, found_data

    def _detailed_search_around_position(self, client, symbol: str, date: str,
                                        center_pos: int, center_time: str) -> List[pd.DataFrame]:
        """在发现的位置周围进行详细搜索"""

        detailed_data = []
        search_range = 1000
        search_step = 100

        # 在中心位置前后进行精细搜索
        search_positions = [
            center_pos - search_range + i * search_step
            for i in range(int(search_range / search_step) * 2 + 1)
            if center_pos - search_range + i * search_step > 0
        ]

        print(f"         🔬 详细搜索位置: {len(search_positions)}个位置")

        for detailed_pos in search_positions:
            try:
                detailed_batch = client.transactions(
                    symbol=symbol, date=date,
                    start=detailed_pos, offset=100  # 较小的批次进行精细搜索
                )

                if detailed_batch is not None and not detailed_batch.empty:
                    detailed_earliest = detailed_batch['time'].iloc[0]
                    detailed_latest = detailed_batch['time'].iloc[-1]

                    # 检查是否有更早的时间
                    if detailed_earliest <= center_time:
                        print(f"            🏅 位置{detailed_pos}: 发现更早时间 {detailed_earliest}")
                        detailed_data.append(detailed_batch)

                    # 如果找到了09:25的数据，立即返回
                    if detailed_earliest <= "09:25":
                        print(f"            🏆 找到09:25数据！位置: {detailed_pos}")
                        detailed_data.append(detailed_batch)
                        break

                time.sleep(0.05)  # 短延迟

            except Exception as e:
                continue

        return detailed_data

    def _contains_target_time(self, data: pd.DataFrame, earliest: str, latest: str) -> bool:
        """检查数据是否包含目标时间段"""

        # 直接检查时间范围
        if earliest <= "09:30" and latest >= "09:20":
            return True

        # 检查数据中是否包含具体的时间点
        times = set(data['time'])
        target_times = {'09:25', '09:24', '09:26', '09:23', '09:27'}

        return len(times & target_times) > 0

    def _get_continuous_data(self, client, symbol: str, date: str) -> List[pd.DataFrame]:
        """获取连续竞价数据"""

        positions = self.key_findings['continuous_strategy']['positions']
        batch_size = self.key_findings['continuous_strategy']['batch_size']

        continuous_data = []
        consecutive_empty = 0

        print(f"   📊 获取连续竞价数据...")

        for i, start_pos in enumerate(positions):
            try:
                print(f"      📦 连续竞价批次{i+1}: start={start_pos}, batch={batch_size}")

                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=batch_size
                )

                self.performance_stats['total_requests'] += 1
                self.performance_stats['continuous_requests'] += 1

                if batch_data is not None and not batch_data.empty:
                    record_count = len(batch_data)
                    current_earliest = batch_data['time'].iloc[0]
                    current_latest = batch_data['time'].iloc[-1]

                    print(f"         ✅ {record_count}条 {current_earliest}-{current_latest}")

                    continuous_data.append(batch_data)
                    consecutive_empty = 0

                    # 智能停止：如果已经到了开盘时间并且获取了足够数据
                    if current_earliest <= "09:30" and i > 2:
                        print(f"         🎯 已覆盖开盘时间，可以停止早期数据获取")
                        break

                else:
                    consecutive_empty += 1
                    print(f"         ❌ 无数据 (连续空:{consecutive_empty})")

                    if consecutive_empty >= 2:
                        print(f"         🛑 连续{consecutive_empty}次无数据，停止")
                        break

                time.sleep(0.1)

            except Exception as e:
                print(f"         ❌ 批次失败: {e}")
                continue

        return continuous_data

    def _integrate_and_validate_data(self, all_data: List[pd.DataFrame], symbol: str) -> pd.DataFrame:
        """整合和验证数据"""

        if not all_data:
            return pd.DataFrame()

        print(f"   🔄 数据整合和验证...")

        # 合并所有数据
        merged_data = pd.concat(all_data, ignore_index=True)
        original_count = len(merged_data)

        # 多维度去重
        merged_data = merged_data.drop_duplicates(subset=['time', 'price', 'vol'])
        after_dedup_count = len(merged_data)

        # 按时间排序
        merged_data = merged_data.sort_values('time').reset_index(drop=True)

        # 添加股票代码
        merged_data['symbol'] = symbol

        # 添加交易阶段标识
        merged_data['trading_phase'] = merged_data['time'].apply(self._identify_trading_phase)

        # 计算累计成交量
        if 'vol' in merged_data.columns:
            merged_data['volume'] = merged_data['vol'].cumsum()

        # 特别标记09:25附近的数据
        merged_data['is_around_0925'] = merged_data['time'].apply(
            lambda x: self._is_around_0925(x)
        )

        # 统计
        duplicate_rate = (original_count - after_dedup_count) / original_count * 100
        self.performance_stats['total_records'] = after_dedup_count

        print(f"      去重: {original_count} → {after_dedup_count} (减少{duplicate_rate:.1f}%)")

        return merged_data

    def _identify_trading_phase(self, time_str: str) -> str:
        """识别交易阶段"""

        try:
            time_obj = datetime.strptime(time_str, '%H:%M')
            hour, minute = time_obj.hour, time_obj.minute

            # 早盘集合竞价
            if hour == 9 and 20 <= minute <= 25:
                return 'pre_market_auction'
            elif hour == 9 and 15 <= minute <= 19:
                return 'early_morning'

            # 连续竞价
            elif (hour == 9 and minute >= 30) or (10 <= hour <= 11 and minute <= 30):
                return 'morning_continuous'
            elif (13 <= hour <= 14) or (hour == 15 and minute == 0):
                return 'afternoon_continuous'

        except:
            pass

        return 'unknown'

    def _is_around_0925(self, time_str: str) -> bool:
        """判断是否在09:25附近"""

        try:
            time_obj = datetime.strptime(time_str, '%H:%M')
            target_time = datetime.strptime('09:25', '%H:%M')
            time_diff = abs((time_obj - target_time).total_seconds() / 60)
            return time_diff <= 5  # 5分钟内
        except:
            return False

    def _analyze_time_coverage_0925(self, final_data: pd.DataFrame):
        """分析09:25数据覆盖情况"""

        if final_data.empty:
            print(f"   ❌ 无数据进行分析")
            return

        earliest_time = final_data['time'].iloc[0]
        latest_time = final_data['time'].iloc[-1]

        self.performance_stats['earliest_time'] = earliest_time

        print(f"\n📊 09:25数据覆盖分析:")
        print(f"   🕐 时间范围: {earliest_time} - {latest_time}")

        # 检查是否包含09:25附近的数据
        around_0925_data = final_data[final_data['is_around_0925'] == True]
        pre_market_data = final_data[final_data['trading_phase'] == 'pre_market_auction']

        if not around_0925_data.empty:
            print(f"   🏅 09:25附近数据: {len(around_0925_data):,}条")
            print(f"   🏅 09:25时间范围: {around_0925_data['time'].iloc[0]} - {around_0925_data['time'].iloc[-1]}")
            self.performance_stats['found_0925_data'] = True
        else:
            print(f"   ❌ 未找到09:25附近数据")
            self.performance_stats['found_0925_data'] = False

        if not pre_market_data.empty:
            print(f"   🏆 早盘集合竞价数据: {len(pre_market_data):,}条")

        # 各时段统计
        phase_stats = final_data['trading_phase'].value_counts()
        print(f"   📈 各时段数据:")
        for phase, count in phase_stats.items():
            phase_names = {
                'pre_market_auction': '早盘集合竞价',
                'early_morning': '早盘交易',
                'morning_continuous': '上午连续竞价',
                'afternoon_continuous': '下午连续竞价'
            }
            phase_name = phase_names.get(phase, phase)
            print(f"      {phase_name}: {count:,}条")

        # 覆盖评估
        if earliest_time <= "09:25":
            print(f"   ✅ 完美覆盖：包含09:25数据")
        elif earliest_time <= "09:30":
            print(f"   ✅ 良好覆盖：接近开盘时间")
        elif earliest_time <= "10:00":
            print(f"   ⚠️ 部分覆盖：开盘后30分钟内")
        else:
            print(f"   ❌ 覆盖不足：开盘30分钟后")

    def print_0925_strategy_performance(self):
        """打印09:25策略性能报告"""

        stats = self.performance_stats
        print(f"\n📊 确保09:25数据策略性能报告:")
        print(f"   🔢 总请求数: {stats['total_requests']}")
        print(f"   🔍 搜索09:25请求: {stats['search_0925_requests']}")
        print(f"   📈 连续竞价请求: {stats['continuous_requests']}")
        print(f"   📅 最早时间: {stats.get('earliest_time', 'N/A')}")
        print(f"   🏅 找到09:25数据: {'是' if stats.get('found_0925_data', False) else '否'}")
        print(f"   📊 总记录数: {stats.get('total_records', 0):,}")


def test_ensure_0925_strategy():
    """测试确保获取09:25数据的策略"""

    print("=" * 80)
    print("🏅 确保获取09:25数据的最优策略测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"核心目标：必须获取09:25开盘前集合竞价数据！")

    from mootdx.quotes import Quotes

    # 测试股票
    test_stocks = [
        ('000001', '平安银行'),
        ('000858', '五粮液'),
    ]

    # 测试日期
    test_dates = []
    for days_back in range(0, 5):
        test_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')
        test_datetime = datetime.strptime(test_date, '%Y%m%d')
        if test_datetime.weekday() < 5:  # 只包含工作日
            test_dates.append(test_date)

    strategy = Ensure0925DataStrategy()

    for symbol, name in test_stocks:
        print(f"\n{'='*60}")
        print(f"🎯 测试股票: {symbol} ({name})")
        print(f"{'='*60}")

        client = Quotes.factory(
            market='std',
            multithread=True,
            heartbeat=True,
            bestip=False,
            timeout=30
        )

        try:
            success_found = False

            for test_date in test_dates:
                print(f"\n📅 尝试日期: {test_date}")

                # 重置统计
                strategy.performance_stats = {
                    'total_requests': 0,
                    'search_0925_requests': 0,
                    'continuous_requests': 0,
                    'found_0925_data': False,
                    'earliest_time': None,
                    'time_coverage': {},
                    'total_records': 0
                }

                result_data = strategy.execute_ensure_0925_strategy(
                    client, symbol, test_date, max_records=30000
                )

                if not result_data.empty:
                    success_found = True

                    print(f"\n🎉 数据获取完成!")
                    print(f"📊 总记录数: {len(result_data):,}")
                    print(f"🕐 时间范围: {result_data['time'].iloc[0]} - {result_data['time'].iloc[-1]}")
                    print(f"💰 价格范围: {result_data['price'].min():.2f} - {result_data['price'].max():.2f}")

                    # 检查09:25数据
                    around_0925 = result_data[result_data['is_around_0925'] == True]
                    if not around_0925.empty:
                        print(f"🏅 09:25附近数据: {len(around_0925):,}条")
                        print(f"🏅 09:25时间: {around_0925['time'].iloc[0]} - {around_0925['time'].iloc[-1]}")
                    else:
                        print(f"⚠️ 未找到09:25附近数据")

                    # 保存数据
                    filename = f"ensure_0925_{symbol}_{test_date}.csv"
                    result_data.to_csv(filename, index=False, encoding='utf-8-sig')
                    print(f"💾 数据保存: {filename}")

                    # 性能报告
                    strategy.print_0925_strategy_performance()

                    break
                else:
                    print(f"❌ {test_date} 无数据")

            if not success_found:
                print(f"❌ 所有日期均无数据")

        except Exception as e:
            print(f"❌ 测试失败: {e}")

        finally:
            client.close()

        print(f"\n⏳ 等待3秒后测试下一只股票...")
        time.sleep(3)


if __name__ == "__main__":
    test_ensure_0925_strategy()
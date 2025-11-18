#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
包含集合竞价的最优历史分笔数据获取策略
确保覆盖完整的A股交易时间：09:15-15:00（含集合竞价）
"""

import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

sys.path.append('/home/bxgh/microservice-stock/services/get-stockdata/src')

class AuctionAwareOptimalTickStrategy:
    def __init__(self):
        """初始化包含集合竞价的最优策略"""

        # 集合竞价时段定义
        self.auction_periods = {
            'morning_auction': ('09:15', '09:25'),  # 早盘集合竞价
            'afternoon_auction': ('12:15', '13:00'), # 午间集合竞价
        }

        # 连续竞价时段定义
        self.continuous_periods = {
            'morning_continuous': ('09:30', '11:30'),
            'afternoon_continuous': ('13:00', '15:00')
        }

        # 针对不同时段的优化策略
        self.auction_strategy = {
            # 集合竞价期间数据稀疏，需要更大的start间隔
            'start_positions': [10000, 12000, 14000, 16000, 18000, 20000, 25000],
            'batch_size': 500,
            'time_target': '09:15'  # 目标时间：集合竞价开始
        }

        # 连续竞价期间数据密集，使用较小的start间隔
        self.continuous_strategy = {
            'start_positions': [0, 300, 600, 1000, 1500, 2000, 3000, 4500, 6000, 8000],
            'batch_size': 400,
            'time_target': '09:30'  # 目标时间：连续竞价开始
        }

        # 股票分类策略
        self.stock_categories = {
            'super_active': {'density_threshold': 30, 'multiplier': 0.8},
            'high_active': {'density_threshold': 15, 'multiplier': 1.0},
            'medium_active': {'density_threshold': 8, 'multiplier': 1.2},
            'low_active': {'density_threshold': 0, 'multiplier': 1.5}
        }

        # 性能统计
        self.performance_stats = {
            'total_requests': 0,
            'auction_requests': 0,
            'continuous_requests': 0,
            'auction_records': 0,
            'continuous_records': 0,
            'earliest_time': None,
            'coverage_complete': False
        }

    def predict_stock_category(self, symbol: str, stock_name: str = None) -> str:
        """预测股票活跃度类别"""

        symbol = symbol.upper()
        stock_name = stock_name.upper() if stock_name else ""

        # 科创板、创业板通常更活跃
        if symbol.startswith('688') or symbol.startswith('300'):
            return 'super_active'

        # 科技股关键词
        tech_keywords = ['科技', '医药', '新能源', '半导体', 'AI', '人工智能', '生物']
        if any(keyword in stock_name for keyword in tech_keywords):
            return 'super_active'

        # 金融股
        if '银行' in stock_name or '保险' in stock_name or '券商' in stock_name:
            return 'high_active'

        # 传统制造
        if any(keyword in stock_name for keyword in ['制造', '化工', '钢铁']):
            return 'medium_active'

        return 'low_active'

    def comprehensive_probe(self, client, symbol: str, date: str) -> Tuple[str, Dict]:
        """综合探测：包含集合竞价和连续竞价时段"""

        print(f"   🔍 综合探测（含集合竞价）...")

        predicted_category = self.predict_stock_category(symbol)
        print(f"   🎯 预判类别: {predicted_category}")

        # 集合竞价探测（使用更大的start值）
        auction_probe_points = [8000, 12000, 16000]  # 集合竞价数据通常在更深的start位置
        auction_densities = []

        print(f"   📊 集合竞价探测:")
        for start_pos in auction_probe_points:
            try:
                sample_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=100
                )

                self.performance_stats['total_requests'] += 1

                if sample_data is not None and not sample_data.empty:
                    time_range = f"{sample_data['time'].iloc[0]}-{sample_data['time'].iloc[-1]}"
                    print(f"      位置{start_pos}: {len(sample_data)}条 ({time_range})")

                    # 检查是否包含集合竞价时间
                    earliest_time = sample_data['time'].iloc[0]
                    if earliest_time <= "09:25":
                        print(f"      ✅ 发现集合竞价数据: {earliest_time}")
                        auction_densities.append(len(sample_data))
                        break
                else:
                    print(f"      位置{start_pos}: 无数据")

            except Exception as e:
                print(f"      位置{start_pos}: 探测失败 - {e}")

        # 连续竞价探测
        continuous_probe_points = [0, 1000, 3000, 5000]
        continuous_densities = []

        print(f"   📊 连续竞价探测:")
        for start_pos in continuous_probe_points:
            try:
                sample_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=150
                )

                self.performance_stats['total_requests'] += 1

                if sample_data is not None and not sample_data.empty:
                    time_range = f"{sample_data['time'].iloc[0]}-{sample_data['time'].iloc[-1]}"
                    print(f"      位置{start_pos}: {len(sample_data)}条 ({time_range})")

                    # 检查是否在连续竞价时段
                    latest_time = sample_data['time'].iloc[-1]
                    if latest_time >= "09:30":
                        time_span = self._calculate_time_span(sample_data)
                        density = len(sample_data) / max(time_span, 1)
                        continuous_densities.append(density)
                        print(f"      📊 密度: {density:.1f}条/分钟")
                else:
                    print(f"      位置{start_pos}: 无数据")

            except Exception as e:
                print(f"      位置{start_pos}: 探测失败 - {e}")

        # 分析探测结果并确定策略
        has_auction = len(auction_densities) > 0
        avg_continuous_density = np.mean(continuous_densities) if continuous_densities else 0

        # 确定股票活跃度类别
        if avg_continuous_density > 30:
            actual_category = 'super_active'
        elif avg_continuous_density > 15:
            actual_category = 'high_active'
        elif avg_continuous_density > 8:
            actual_category = 'medium_active'
        else:
            actual_category = 'low_active'

        # 生成定制化策略
        custom_strategy = self._generate_custom_strategy(actual_category, has_auction)

        print(f"   ✅ 最终类别: {actual_category}")
        print(f"   🏅 集合竞价: {'✅有' if has_auction else '❌无'}")
        print(f"   📊 连续竞价密度: {avg_continuous_density:.1f}条/分钟")

        return actual_category, custom_strategy

    def _generate_custom_strategy(self, category: str, has_auction: bool) -> Dict:
        """生成定制化的获取策略"""

        base_multiplier = self.stock_categories[category]['multiplier']

        # 根据是否有集合竞价数据调整策略
        if has_auction:
            # 发现集合竞价数据，需要更深的探测
            auction_positions = [12000, 14000, 16000, 18000, 20000, 23000, 26000]
            auction_batch = int(400 * base_multiplier)
        else:
            # 没有发现集合竞价数据，使用较浅的探测
            auction_positions = [6000, 8000, 10000, 12000, 15000]
            auction_batch = int(300 * base_multiplier)

        # 连续竞价策略
        if category == 'super_active':
            continuous_positions = [0, 200, 400, 700, 1000, 1400, 1900, 2500]
        elif category == 'high_active':
            continuous_positions = [0, 300, 600, 1000, 1500, 2100, 2800]
        elif category == 'medium_active':
            continuous_positions = [0, 500, 1000, 1600, 2300, 3100, 4000]
        else:
            continuous_positions = [0, 800, 1600, 2400, 3300, 4300, 5500]

        continuous_batch = int(400 * base_multiplier)

        return {
            'auction_positions': auction_positions,
            'auction_batch': auction_batch,
            'continuous_positions': continuous_positions,
            'continuous_batch': continuous_batch,
            'has_auction': has_auction
        }

    def execute_comprehensive_fetch(self, client, symbol: str, date: str, max_records: int = 30000):
        """执行包含集合竞价的综合获取策略"""

        print(f"🚀 执行包含集合竞价的综合获取策略: {symbol} {date}")

        start_time = time.time()

        # 第一步：综合探测
        actual_category, strategy = self.comprehensive_probe(client, symbol, date)

        print(f"\n   📋 执行策略:")
        print(f"      集合竞价: {strategy['auction_positions'][:3]}... (批次:{strategy['auction_batch']})")
        print(f"      连续竞价: {strategy['continuous_positions'][:5]}... (批次:{strategy['continuous_batch']})")

        all_data = []
        earliest_time_found = None
        latest_time_found = None
        total_retrieved = 0

        # 第二步：获取集合竞价数据（如果策略支持）
        if strategy['has_auction']:
            print(f"\n   📊 步骤1: 获取集合竞价数据...")
            self._fetch_auction_data(
                client, symbol, date, strategy, all_data,
                earliest_time_found, total_retrieved, max_records
            )

        # 第三步：获取连续竞价数据
        print(f"\n   📊 步骤2: 获取连续竞价数据...")
        self._fetch_continuous_data(
            client, symbol, date, strategy, all_data,
            earliest_time_found, total_retrieved, max_records
        )

        # 第四步：数据后处理
        final_data = self._process_comprehensive_data(all_data, symbol)

        # 计算执行时间
        execution_time = time.time() - start_time

        # 分析时间覆盖情况
        self._analyze_time_coverage(final_data)

        print(f"\n   ⏱️ 总执行时间: {execution_time:.2f}秒")

        return final_data

    def _fetch_auction_data(self, client, symbol, date, strategy, all_data,
                           earliest_time_found, total_retrieved, max_records):
        """获取集合竞价数据"""

        positions = strategy['auction_positions']
        batch_size = strategy['auction_batch']

        for i, start_pos in enumerate(positions):
            if total_retrieved >= max_records:
                break

            try:
                print(f"   📦 集合竞价批次{i+1}: start={start_pos}, batch={batch_size}")

                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=batch_size
                )

                self.performance_stats['total_requests'] += 1
                self.performance_stats['auction_requests'] += 1

                if batch_data is not None and not batch_data.empty:
                    record_count = len(batch_data)
                    current_earliest = batch_data['time'].iloc[0]
                    current_latest = batch_data['time'].iloc[-1]

                    print(f"      ✅ {record_count}条 {current_earliest}-{current_latest}")

                    # 检查是否包含集合竞价时间
                    if current_earliest <= "09:25":
                        print(f"      🏅 发现集合竞价时段数据!")

                    # 检查数据新颖性
                    if self._is_new_data(batch_data, all_data):
                        all_data.append(batch_data)
                        total_retrieved += record_count
                        self.performance_stats['auction_records'] += record_count

                        if earliest_time_found is None or current_earliest < earliest_time_found:
                            earliest_time_found = current_earliest

                    # 如果已经到达集合竞价开始时间，停止 deeper 探测
                    if current_earliest <= "09:15":
                        print(f"      🎯 已到达集合竞价开始时间")
                        break
                else:
                    print(f"      ❌ 无数据")
                    break

                time.sleep(0.15)  # 稍长的延迟避免压力

            except Exception as e:
                print(f"      ❌ 批次失败: {e}")
                continue

    def _fetch_continuous_data(self, client, symbol, date, strategy, all_data,
                              earliest_time_found, total_retrieved, max_records):
        """获取连续竞价数据"""

        positions = strategy['continuous_positions']
        batch_size = strategy['continuous_batch']

        for i, start_pos in enumerate(positions):
            if total_retrieved >= max_records:
                break

            try:
                print(f"   📦 连续竞价批次{i+1}: start={start_pos}, batch={batch_size}")

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

                    print(f"      ✅ {record_count}条 {current_earliest}-{current_latest}")

                    # 检查数据新颖性
                    if self._is_new_data(batch_data, all_data):
                        all_data.append(batch_data)
                        total_retrieved += record_count
                        self.performance_stats['continuous_records'] += record_count

                        if earliest_time_found is None or current_earliest < earliest_time_found:
                            earliest_time_found = current_earliest

                    # 如果已经到达开盘时间，可以停止早期数据的获取
                    if earliest_time_found and earliest_time_found <= "09:30":
                        if i > 2:  # 至少获取几个批次确保数据质量
                            print(f"      🎯 已覆盖开盘时间，可以停止早期探测")
                            break
                else:
                    print(f"      ❌ 无数据")
                    # 连续竞价阶段的无数据可能意味着到了数据边界
                    if i > 3:
                        print(f"      🛑 连续竞价阶段连续无数据，可能到达边界")
                        break

                time.sleep(0.1)

            except Exception as e:
                print(f"      ❌ 批次失败: {e}")
                continue

    def _is_new_data(self, new_data: pd.DataFrame, existing_data: List[pd.DataFrame]) -> bool:
        """检查数据是否为新的"""

        if not existing_data:
            return True

        new_times = set(new_data['time'])

        for data in existing_data:
            if not data.empty:
                existing_times = set(data['time'])
                overlap = len(new_times & existing_times)

                if overlap > len(new_times) * 0.7:  # 70%重叠阈值
                    return False

        return True

    def _calculate_time_span(self, data: pd.DataFrame) -> float:
        """计算时间跨度"""

        if data.empty or len(data) < 2:
            return 1.0

        try:
            times = data['time'].tolist()
            time_objects = []

            for t in times[:3]:
                try:
                    time_obj = datetime.strptime(str(t), '%H:%M')
                    time_objects.append(time_obj)
                except:
                    continue

            if len(time_objects) >= 2:
                span = (time_objects[-1] - time_objects[0]).total_seconds() / 60
                return max(span, 1.0)

        except:
            pass

        return 1.0

    def _process_comprehensive_data(self, all_data: List[pd.DataFrame], symbol: str) -> pd.DataFrame:
        """处理综合数据"""

        if not all_data:
            return pd.DataFrame()

        print(f"   🔄 综合数据处理...")

        # 合并所有数据
        merged_data = pd.concat(all_data, ignore_index=True)
        original_count = len(merged_data)

        # 多维度去重
        merged_data = merged_data.drop_duplicates(subset=['time', 'price', 'vol'])
        after_dedup_count = len(merged_data)

        # 按时间排序
        merged_data = merged_data.sort_values('time').reset_index(drop=True)

        # 添加股票代码和交易阶段标识
        merged_data['symbol'] = symbol
        merged_data['trading_phase'] = merged_data['time'].apply(self._identify_trading_phase)

        # 计算累计成交量
        if 'vol' in merged_data.columns:
            merged_data['volume'] = merged_data['vol'].cumsum()

        print(f"      去重: {original_count} → {after_dedup_count} (减少{(original_count-after_dedup_count)/original_count*100:.1f}%)")

        return merged_data

    def _identify_trading_phase(self, time_str: str) -> str:
        """识别交易阶段"""

        try:
            time_obj = datetime.strptime(time_str, '%H:%M')
            time_only = time_obj.time()

            # 集合竞价时段
            if time_obj.hour == 9 and 15 <= time_obj.minute <= 25:
                return 'morning_auction'
            elif (time_obj.hour == 12 and 15 <= time_obj.minute <= 59) or \
                 (time_obj.hour == 13 and 0 <= time_obj.minute <= 0):
                return 'afternoon_auction'

            # 连续竞价时段
            elif (time_obj.hour == 9 and 30 <= time_obj.minute <= 59) or \
                 (time_obj.hour == 10) or \
                 (time_obj.hour == 11 and 0 <= time_obj.minute <= 30):
                return 'morning_continuous'
            elif (time_obj.hour == 13 and 0 <= time_obj.minute <= 59) or \
                 (time_obj.hour == 14) or \
                 (time_obj.hour == 15 and 0 <= time_obj.minute <= 0):
                return 'afternoon_continuous'

        except:
            pass

        return 'unknown'

    def _analyze_time_coverage(self, final_data: pd.DataFrame):
        """分析时间覆盖情况"""

        if final_data.empty:
            print(f"   ❌ 无数据进行时间覆盖分析")
            return

        earliest_time = final_data['time'].iloc[0]
        latest_time = final_data['time'].iloc[-1]

        self.performance_stats['earliest_time'] = earliest_time

        # 检查各个时段的覆盖情况
        phases = final_data['trading_phase'].value_counts()
        print(f"\n   📅 时间覆盖分析:")
        print(f"      时间范围: {earliest_time} - {latest_time}")

        for phase, count in phases.items():
            phase_names = {
                'morning_auction': '早盘集合竞价',
                'afternoon_auction': '午间集合竞价',
                'morning_continuous': '上午连续竞价',
                'afternoon_continuous': '下午连续竞价'
            }
            phase_name = phase_names.get(phase, phase)
            print(f"      {phase_name}: {count:,}条记录")

        # 检查是否覆盖完整交易日
        coverage_complete = False
        if earliest_time <= "09:25" and latest_time >= "15:00":
            coverage_complete = True
            print(f"      ✅ 完整交易日覆盖 (09:25-15:00)")
        elif earliest_time <= "09:30" and latest_time >= "15:00":
            coverage_complete = True
            print(f"      ✅ 完整连续竞价覆盖 (09:30-15:00)")
        else:
            print(f"      ⚠️ 部分覆盖，不完整")

        self.performance_stats['coverage_complete'] = coverage_complete

    def print_comprehensive_performance_report(self):
        """打印综合性能报告"""

        stats = self.performance_stats
        print(f"\n📊 包含集合竞价的综合性能报告:")
        print(f"   🔢 总请求数: {stats['total_requests']}")
        print(f"   📊 集合竞价请求: {stats['auction_requests']}")
        print(f"   📈 连续竞价请求: {stats['continuous_requests']}")
        print(f"   🏅 集合竞价记录: {stats['auction_records']:,}")
        print(f"   ⚡ 连续竞价记录: {stats['continuous_records']:,}")
        print(f"   📅 最早时间: {stats.get('earliest_time', 'N/A')}")
        print(f"   ✅ 完整覆盖: {'是' if stats.get('coverage_complete', False) else '否'}")


def test_auction_aware_strategy():
    """测试包含集合竞价的最优策略"""

    print("=" * 80)
    print("🏅 包含集合竞价的最优历史分笔数据获取策略测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    from mootdx.quotes import Quotes

    # 测试股票
    test_stocks = [
        ('000001', '平安银行'),
        ('000858', '五粮液'),
    ]

    # 测试日期（最近的交易日）
    test_dates = []
    for days_back in range(0, 5):
        test_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')
        test_datetime = datetime.strptime(test_date, '%Y%m%d')
        if test_datetime.weekday() < 5:  # 只包含工作日
            test_dates.append(test_date)

    strategy = AuctionAwareOptimalTickStrategy()

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
                    'auction_requests': 0,
                    'continuous_requests': 0,
                    'auction_records': 0,
                    'continuous_records': 0,
                    'earliest_time': None,
                    'coverage_complete': False
                }

                result_data = strategy.execute_comprehensive_fetch(
                    client, symbol, test_date, max_records=25000
                )

                if not result_data.empty:
                    success_found = True

                    print(f"\n🎉 成功获取完整交易日数据!")
                    print(f"📊 总记录数: {len(result_data):,}")
                    print(f"🕐 时间范围: {result_data['time'].iloc[0]} - {result_data['time'].iloc[-1]}")
                    print(f"💰 价格范围: {result_data['price'].min():.2f} - {result_data['price'].max():.2f}")

                    # 分析集合竞价数据
                    auction_data = result_data[result_data['trading_phase'].str.contains('auction')]
                    if not auction_data.empty:
                        print(f"🏅 集合竞价记录: {len(auction_data):,}条")
                        print(f"🏅 集合竞价时间: {auction_data['time'].iloc[0]} - {auction_data['time'].iloc[-1]}")
                    else:
                        print(f"⚠️ 未发现集合竞价数据")

                    # 保存数据
                    filename = f"auction_aware_{symbol}_{test_date}.csv"
                    result_data.to_csv(filename, index=False, encoding='utf-8-sig')
                    print(f"💾 完整数据保存: {filename}")

                    # 性能报告
                    strategy.print_comprehensive_performance_report()

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
    test_auction_aware_strategy()
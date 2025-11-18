#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版最优历史分笔数据获取策略
基于实际测试结果优化的终极策略
"""

import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

sys.path.append('/home/bxgh/microservice-stock/services/get-stockdata/src')

class FixedOptimalTickStrategy:
    def __init__(self):
        """初始化修复版最优策略"""

        # 修正后的策略参数（基于实际测试）
        self.stock_categories = {
            # 超级活跃股 - 小批次，高频率
            'super_active': {
                'start_positions': [0, 200, 400, 600, 800, 1000, 1200, 1500, 2000],
                'batch_size': 300,
                'probe_batch': 50
            },

            # 高活跃股 - 平衡策略
            'high_active': {
                'start_positions': [0, 300, 600, 1000, 1500, 2000, 3000, 4500],
                'batch_size': 400,
                'probe_batch': 80
            },

            # 中活跃股 - 中等批次
            'medium_active': {
                'start_positions': [0, 500, 1000, 1500, 2500, 4000, 6000, 8000],
                'batch_size': 500,
                'probe_batch': 100
            },

            # 低活跃股 - 大批次，低频率
            'low_active': {
                'start_positions': [0, 800, 1800, 3000, 5000, 7500, 10000],
                'batch_size': 600,
                'probe_batch': 150
            }
        }

        # 性能统计
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'data_records': 0,
            'duplicate_rate': 0,
            'coverage_rate': 0,
            'execution_time': 0
        }

    def predict_stock_category(self, symbol: str, stock_name: str = None) -> str:
        """基于静态特征预判股票类别"""

        symbol = symbol.upper()
        stock_name = stock_name.upper() if stock_name else ""

        # 科创板、创业板 = 超级活跃
        if symbol.startswith('688') or symbol.startswith('300'):
            return 'super_active'

        # 科技股关键词
        tech_keywords = ['科技', '医药', '新能源', '半导体', 'AI', '人工智能', '生物', '软件']
        if any(keyword in stock_name for keyword in tech_keywords):
            return 'super_active'

        # 金融股
        finance_keywords = ['银行', '保险', '券商', '信托']
        if any(keyword in stock_name for keyword in finance_keywords):
            return 'high_active'

        # 传统行业
        traditional_keywords = ['制造', '化工', '钢铁', '汽车', '机械']
        if any(keyword in stock_name for keyword in traditional_keywords):
            return 'medium_active'

        # 默认低活跃
        return 'low_active'

    def rapid_probe(self, client, symbol: str, date: str) -> Tuple[str, Dict]:
        """快速探测验证（修正版）"""

        print(f"   ⚡ 快速探测验证...")

        predicted_category = self.predict_stock_category(symbol)
        base_strategy = self.stock_categories[predicted_category]

        # 使用更小的探测批次
        probe_points = [0, 1000, 3000]
        probe_batch = base_strategy['probe_batch']

        densities = []
        found_data = []

        for start_pos in probe_points:
            try:
                sample_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=probe_batch
                )

                self.performance_stats['total_requests'] += 1

                if sample_data is not None and not sample_data.empty:
                    # 计算时间跨度
                    time_span = self._calculate_time_span(sample_data)
                    density = len(sample_data) / max(time_span, 1)

                    densities.append(density)
                    found_data.append(start_pos)

                    print(f"      位置{start_pos}: {density:.1f}条/分钟 ({len(sample_data)}条)")
                else:
                    print(f"      位置{start_pos}: 无数据")

            except Exception as e:
                print(f"      位置{start_pos}: 探测失败 - {e}")
                continue

        # 确定实际类别
        if densities:
            avg_density = np.mean(densities)
            print(f"   📊 平均密度: {avg_density:.1f}条/分钟")

            if avg_density > 25:
                actual_category = 'super_active'
            elif avg_density > 15:
                actual_category = 'high_active'
            elif avg_density > 8:
                actual_category = 'medium_active'
            else:
                actual_category = 'low_active'

            if actual_category != predicted_category:
                print(f"   🔄 策略调整: {predicted_category} → {actual_category}")
        else:
            actual_category = 'low_active'
            print(f"   ⚠️ 无探测数据，使用默认策略: {actual_category}")

        # 选择策略并基于探测结果微调
        strategy = self.stock_categories[actual_category].copy()

        # 如果发现了数据位置，调整策略
        if found_data:
            max_start = max(found_data)
            if max_start > 0:
                # 确保策略包含已发现的位置
                if max_start not in strategy['start_positions']:
                    strategy['start_positions'].append(max_start)
                    strategy['start_positions'].sort()

        return actual_category, strategy

    def execute_fixed_optimal_fetch(self, client, symbol: str, date: str, max_records: int = 20000):
        """执行修复版最优获取策略"""

        print(f"🚀 执行修复版最优策略: {symbol} {date}")

        start_time = time.time()

        # 第一步：预判和探测
        predicted_category = self.predict_stock_category(symbol)
        print(f"   🎯 预判类别: {predicted_category}")

        actual_category, optimal_strategy = self.rapid_probe(client, symbol, date)

        print(f"   ✅ 确认类别: {actual_category}")
        print(f"   📋 最优策略: {optimal_strategy['start_positions'][:5]}... 批次:{optimal_strategy['batch_size']}")

        # 第二步：执行获取
        all_data = []
        strategy_positions = optimal_strategy['start_positions']
        batch_size = optimal_strategy['batch_size']

        consecutive_empty = 0
        total_retrieved = 0
        earliest_time = None

        print(f"\n   🎯 执行数据获取...")

        for i, start_pos in enumerate(strategy_positions):
            if total_retrieved >= max_records:
                break

            print(f"   📦 批次{i+1}: start={start_pos}, batch={batch_size}")

            try:
                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=batch_size
                )

                self.performance_stats['total_requests'] += 1

                if batch_data is not None and not batch_data.empty:
                    consecutive_empty = 0
                    record_count = len(batch_data)
                    current_earliest = batch_data['time'].iloc[0]
                    current_latest = batch_data['time'].iloc[-1]

                    print(f"      ✅ {record_count}条 {current_earliest}-{current_latest}")

                    # 更新时间范围
                    if earliest_time is None or current_earliest < earliest_time:
                        earliest_time = current_earliest
                        print(f"      🏁 新最早时间: {earliest_time}")

                    # 检查数据重复度
                    is_new_data = self._check_data_overlap(batch_data, all_data)

                    if is_new_data:
                        all_data.append(batch_data)
                        total_retrieved += record_count
                        print(f"      📊 累计: {len(all_data)}数据集, {total_retrieved}条记录")
                    else:
                        print(f"      ⚠️ 数据重复，跳过")

                    # 智能停止条件
                    if earliest_time and earliest_time <= "09:30":
                        print(f"      🏅 已获取开盘数据，停止早期探测")
                        break

                    # 如果已经获取了足够的最新数据，可以适当减少探测
                    if earliest_time and earliest_time <= "10:00":
                        print(f"      ⏰ 已覆盖主要交易时段，可以停止")
                        break

                else:
                    consecutive_empty += 1
                    print(f"      ❌ 无数据 (连续空:{consecutive_empty})")

                    if consecutive_empty >= 3:
                        print(f"      🛑 连续{consecutive_empty}次无数据，停止")
                        break

                # 智能延迟
                time.sleep(0.1)  # 固定100ms延迟

            except Exception as e:
                print(f"      ❌ 批次失败: {e}")
                continue

        # 数据后处理
        final_data = self._process_final_data(all_data, symbol)

        # 计算执行时间
        execution_time = time.time() - start_time
        self.performance_stats['execution_time'] = execution_time

        return final_data

    def _check_data_overlap(self, new_data: pd.DataFrame, existing_data: List[pd.DataFrame]) -> bool:
        """检查数据重叠度"""

        if not existing_data:
            return True

        new_times = set(new_data['time'])

        for data in existing_data:
            if not data.empty:
                existing_times = set(data['time'])
                overlap = len(new_times & existing_times)

                # 重叠度超过70%认为是重复数据
                if overlap > len(new_times) * 0.7:
                    return False

        return True

    def _calculate_time_span(self, data: pd.DataFrame) -> float:
        """计算数据时间跨度（分钟）"""

        if data.empty or len(data) < 2:
            return 1.0

        try:
            # 尝试不同的时间格式
            times = data['time'].tolist()
            time_objects = []

            for t in times[:5]:  # 只检查前5条时间
                try:
                    if ':' in str(t):
                        time_obj = datetime.strptime(str(t), '%H:%M')
                    else:
                        # 如果是其他格式，跳过
                        continue
                    time_objects.append(time_obj)
                except:
                    continue

            if len(time_objects) >= 2:
                span = (time_objects[-1] - time_objects[0]).total_seconds() / 60
                return max(span, 1.0)

        except:
            pass

        return 1.0

    def _process_final_data(self, all_data: List[pd.DataFrame], symbol: str) -> pd.DataFrame:
        """数据处理和统计"""

        if not all_data:
            return pd.DataFrame()

        print(f"   🔄 数据后处理...")

        # 合并数据
        merged_data = pd.concat(all_data, ignore_index=True)
        original_count = len(merged_data)

        # 去重
        merged_data = merged_data.drop_duplicates(subset=['time', 'price', 'vol'])
        after_dedup_count = len(merged_data)

        # 排序
        merged_data = merged_data.sort_values('time').reset_index(drop=True)

        # 添加股票代码
        merged_data['symbol'] = symbol

        # 累计成交量
        if 'vol' in merged_data.columns:
            merged_data['volume'] = merged_data['vol'].cumsum()

        # 统计
        duplicate_rate = (original_count - after_dedup_count) / original_count * 100
        self.performance_stats['duplicate_rate'] = duplicate_rate
        self.performance_stats['data_records'] = after_dedup_count

        print(f"      去重: {original_count} → {after_dedup_count} (减少{duplicate_rate:.1f}%)")

        return merged_data

    def print_performance_report(self):
        """打印性能报告"""

        stats = self.performance_stats
        print(f"\n📊 修复版策略性能报告:")
        print(f"   🔢 总请求数: {stats['total_requests']}")
        print(f"   ✅ 成功请求: {stats['successful_requests']}")
        print(f"   📈 数据记录: {stats['data_records']:,}")
        print(f"   🔄 去重率: {stats['duplicate_rate']:.1f}%")
        print(f"   ⏱️ 执行时间: {stats['execution_time']:.2f}秒")

        if stats['total_requests'] > 0:
            efficiency = stats['data_records'] / stats['total_requests']
            speed = stats['data_records'] / stats['execution_time'] if stats['execution_time'] > 0 else 0
            print(f"   ⚡ 获取效率: {efficiency:.0f}条/请求")
            print(f"   🚀 获取速度: {speed:.0f}条/秒")


def test_fixed_optimal_strategy():
    """测试修复版最优策略"""

    print("=" * 80)
    print("🔧 修复版最优历史分笔数据获取策略测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    from mootdx.quotes import Quotes

    # 测试多只股票
    test_cases = [
        ('000001', '平安银行'),  # 金融股
        ('000858', '五粮液'),    # 消费股
        ('002415', '海康威视'),  # 科技股
    ]

    # 尝试多个日期
    test_dates = []
    for days_back in range(0, 7):
        test_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')
        test_datetime = datetime.strptime(test_date, '%Y%m%d')
        if test_datetime.weekday() < 5:  # 只包含工作日
            test_dates.append(test_date)

    print(f"📅 测试日期: {test_dates}")

    strategy = FixedOptimalTickStrategy()

    for symbol, name in test_cases:
        print(f"\n{'='*60}")
        print(f"🎯 测试股票: {symbol} ({name})")
        print(f"{'='*60}")

        # 创建客户端
        client = Quotes.factory(
            market='std',
            multithread=True,
            heartbeat=True,
            bestip=False,
            timeout=30
        )

        try:
            # 寻找有数据的日期
            success_found = False

            for test_date in test_dates:
                print(f"\n📅 尝试日期: {test_date}")

                # 重置统计
                strategy.performance_stats = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'data_records': 0,
                    'duplicate_rate': 0,
                    'coverage_rate': 0,
                    'execution_time': 0
                }

                result_data = strategy.execute_fixed_optimal_fetch(
                    client, symbol, test_date, max_records=15000
                )

                if not result_data.empty:
                    success_found = True

                    print(f"\n🎉 成功获取数据!")
                    print(f"📊 记录数: {len(result_data):,}")
                    print(f"🕐 时间范围: {result_data['time'].iloc[0]} - {result_data['time'].iloc[-1]}")
                    print(f"💰 价格范围: {result_data['price'].min():.2f} - {result_data['price'].max():.2f}")

                    # 保存数据
                    filename = f"fixed_optimal_{symbol}_{test_date}.csv"
                    result_data.to_csv(filename, index=False, encoding='utf-8-sig')
                    print(f"💾 数据保存: {filename}")

                    # 性能报告
                    strategy.print_performance_report()

                    break
                else:
                    print(f"❌ {test_date} 无数据")

            if not success_found:
                print(f"❌ 所有日期均无数据")

        except Exception as e:
            print(f"❌ 测试失败: {e}")

        finally:
            client.close()

        print(f"\n⏳ 等待2秒后测试下一只股票...")
        time.sleep(2)


if __name__ == "__main__":
    test_fixed_optimal_strategy()
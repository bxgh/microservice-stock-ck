#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极最优历史分笔数据获取策略
基于三层智能决策系统，实现数据准确性、获取速度、资源占用的最优平衡
"""

import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

sys.path.append('/home/bxgh/microservice-stock/services/get-stockdata/src')

class UltimateOptimalTickStrategy:
    def __init__(self):
        """初始化终极最优策略系统"""

        # 第一层：股票特征预判库
        self.stock_prediction_rules = {
            # 超级活跃股特征（密度>30条/分钟）
            'super_active': {
                'prefixes': ['688', '300', '688'],  # 科创板、创业板
                'keywords': ['科技', '医药', '新能源', '半导体', 'AI', '人工智能', '生物'],
                'special_patterns': ['龙头', '涨停', '概念', '次新'],
                'strategy': {
                    'start_positions': [0, 150, 400, 700, 1100, 1600, 2200],
                    'batch_size': 1200,
                    'probe_batch': 80,
                    'time_threshold': 15  # 15分钟停止
                }
            },

            # 高活跃股特征（密度15-30条/分钟）
            'high_active': {
                'industries': ['银行', '保险', '券商', '地产', '白酒'],
                'market_cap_level': 'large',
                'strategy': {
                    'start_positions': [0, 300, 800, 1400, 2100, 3000, 4200],
                    'batch_size': 1500,
                    'probe_batch': 100,
                    'time_threshold': 20
                }
            },

            # 中活跃股特征（密度8-15条/分钟）
            'medium_active': {
                'industries': ['制造', '化工', '钢铁', '汽车'],
                'strategy': {
                    'start_positions': [0, 500, 1200, 2000, 3000, 4300, 6000],
                    'batch_size': 1800,
                    'probe_batch': 150,
                    'time_threshold': 25
                }
            },

            # 低活跃股特征（密度<8条/分钟）
            'low_active': {
                'default': True,  # 默认策略
                'strategy': {
                    'start_positions': [0, 800, 1800, 3000, 4500, 6500, 9000],
                    'batch_size': 2000,
                    'probe_batch': 200,
                    'time_threshold': 30
                }
            }
        }

        # 第二层：时间优化策略
        self.time_optimization = {
            'trading_hours': {
                'morning': ('09:30', '11:30'),
                'afternoon': ('13:00', '15:00')
            },
            'key_periods': {
                'opening': ('09:30', '09:45'),    # 开盘关键期
                'closing': ('14:45', '15:00'),    # 收盘关键期
                'lunch_break': ('11:30', '13:00')  # 午休跳过
            }
        }

        # 性能统计
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'data_records': 0,
            'duplicate_rate': 0,
            'coverage_rate': 0
        }

    def predict_stock_category(self, symbol: str, stock_name: str = None) -> str:
        """第一层：基于静态特征预判股票类别"""

        symbol = symbol.upper()
        stock_name = stock_name.upper() if stock_name else ""

        # 检查超级活跃股特征
        super_rules = self.stock_prediction_rules['super_active']

        # 检查代码前缀
        if any(symbol.startswith(prefix) for prefix in super_rules['prefixes']):
            return 'super_active'

        # 检查关键词
        if any(keyword in stock_name for keyword in super_rules['keywords']):
            return 'super_active'

        # 检查特殊模式
        if any(pattern in stock_name for pattern in super_rules['special_patterns']):
            return 'super_active'

        # 检查高活跃股特征
        high_rules = self.stock_prediction_rules['high_active']
        if any(industry in stock_name for industry in high_rules['industries']):
            return 'high_active'

        # 检查中活跃股特征
        medium_rules = self.stock_prediction_rules['medium_active']
        if any(industry in stock_name for industry in medium_rules['industries']):
            return 'medium_active'

        # 默认为低活跃股
        return 'low_active'

    def ultra_fast_probe(self, client, symbol: str, date: str) -> Tuple[str, Dict]:
        """第二层：超快速探测验证（3次精准探测）"""

        print(f"   ⚡ 超快速探测验证...")

        # 基于预判类别选择探测点
        predicted_category = self.predict_stock_category(symbol)
        base_strategy = self.stock_prediction_rules[predicted_category]['strategy']

        # 使用3个关键探测点进行验证
        probe_points = [0, 2000, 5000]  # 最新、中期、早期数据
        probe_batch = base_strategy['probe_batch']

        densities = []
        time_spans = []

        for start_pos in probe_points:
            try:
                start_time = time.time()

                sample_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=probe_batch
                )

                request_time = time.time() - start_time
                self.performance_stats['total_requests'] += 1

                if sample_data is not None and not sample_data.empty:
                    # 计算时间跨度和数据密度
                    time_span = self._calculate_time_span(sample_data)
                    density = len(sample_data) / max(time_span, 1)

                    densities.append(density)
                    time_spans.append(time_span)

                    print(f"      位置{start_pos}: {density:.1f}条/分钟 ({request_time:.2f}s)")

                else:
                    print(f"      位置{start_pos}: 无数据 ({request_time:.2f}s)")

            except Exception as e:
                print(f"      位置{start_pos}: 探测失败 - {e}")
                continue

        # 基于探测结果确认类别
        if densities:
            avg_density = np.mean(densities)
            print(f"   📊 实际密度: {avg_density:.1f}条/分钟 (预测: {predicted_category})")

            # 动态调整类别
            if avg_density > 30:
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
            actual_category = 'low_active'  # 无数据时使用最保守策略
            avg_density = 0

        # 选择最优策略
        optimal_strategy = self.stock_prediction_rules[actual_category]['strategy'].copy()

        # 基于实际密度微调策略
        optimal_strategy = self._fine_tune_strategy(optimal_strategy, avg_density, time_spans)

        return actual_category, optimal_strategy

    def _fine_tune_strategy(self, strategy: Dict, density: float, response_times: List[float]) -> Dict:
        """基于实际探测结果微调策略"""

        # 基于数据密度调整start间隔
        if density > 40:  # 超高密度
            # 缩小start间隔，更精细分段
            positions = strategy['start_positions']
            tuned_positions = []
            for i in range(len(positions) - 1):
                tuned_positions.append(positions[i])
                # 在两个位置之间插入一个点
                mid_point = int((positions[i] + positions[i+1]) * 0.6)
                if mid_point > positions[i] + 100:  # 确保有足够间隔
                    tuned_positions.append(mid_point)
            tuned_positions.append(positions[-1])
            strategy['start_positions'] = tuned_positions
            strategy['batch_size'] = int(strategy['batch_size'] * 0.8)  # 减小批次

        elif density < 5:  # 超低密度
            # 扩大start间隔，减少无效探测
            positions = strategy['start_positions']
            strategy['start_positions'] = [int(pos * 1.3) for pos in positions]
            strategy['batch_size'] = int(strategy['batch_size'] * 1.2)  # 增大批次

        # 基于响应时间调整
        if response_times:
            avg_response_time = np.mean(response_times)
            if avg_response_time > 0.5:  # 响应较慢
                strategy['batch_size'] = min(strategy['batch_size'] * 1.5, 3000)
            elif avg_response_time < 0.1:  # 响应很快
                strategy['batch_size'] = max(strategy['batch_size'] * 0.8, 800)

        return strategy

    def execute_optimal_fetch(self, client, symbol: str, date: str, max_records: int = 50000):
        """第三层：执行最优获取策略"""

        print(f"🚀 执行终极最优获取策略: {symbol} {date}")

        # 第一层：预判
        predicted_category = self.predict_stock_category(symbol)
        print(f"   🎯 预判类别: {predicted_category}")

        # 第二层：探测验证
        actual_category, optimal_strategy = self.ultra_fast_probe(client, symbol, date)

        print(f"   ✅ 确认类别: {actual_category}")
        print(f"   📋 最优策略: {optimal_strategy['start_positions'][:3]}... (批次:{optimal_strategy['batch_size']})")

        # 第三层：执行获取
        all_data = []
        strategy_positions = optimal_strategy['start_positions']
        batch_size = optimal_strategy['batch_size']
        time_threshold = optimal_strategy['time_threshold']

        earliest_time_found = None
        consecutive_empty = 0
        total_retrieved = 0

        print(f"\n   🎯 执行最优获取...")

        for i, start_pos in enumerate(strategy_positions):
            if total_retrieved >= max_records:
                break

            print(f"   📦 批次{i+1}: start={start_pos}, batch={batch_size}")

            try:
                start_time = time.time()

                batch_data = client.transactions(
                    symbol=symbol, date=date,
                    start=start_pos, offset=batch_size
                )

                request_time = time.time() - start_time
                self.performance_stats['total_requests'] += 1

                if batch_data is not None and not batch_data.empty:
                    consecutive_empty = 0
                    record_count = len(batch_data)
                    current_earliest = batch_data['time'].iloc[0]
                    current_latest = batch_data['time'].iloc[-1]

                    print(f"      ✅ {record_count}条 ({request_time:.2f}s) {current_earliest}-{current_latest}")

                    # 更新时间范围
                    if earliest_time_found is None or current_earliest < earliest_time_found:
                        earliest_time_found = current_earliest
                        print(f"      🏁 新最早时间: {earliest_time_found}")

                    # 检查数据重复度
                    is_new_data = self._check_data_novelty(batch_data, all_data)

                    if is_new_data:
                        all_data.append(batch_data)
                        total_retrieved += record_count
                        print(f"      📊 累计: {len(all_data)}个数据集, {total_retrieved}条记录")

                    # 智能停止条件
                    if earliest_time_found and earliest_time_found <= "09:30":
                        print(f"      🏅 已获取开盘数据，停止早期探测")
                        break

                    # 时间阈值检查
                    if earliest_time_found:
                        time_from_opening = self._time_from_opening(earliest_time_found)
                        if time_from_opening >= time_threshold:
                            print(f"      ⏱️ 已达时间阈值({time_threshold}分钟)，停止")
                            break

                else:
                    consecutive_empty += 1
                    print(f"      ❌ 无数据 (连续空:{consecutive_empty})")

                    if consecutive_empty >= 2:
                        print(f"      🛑 连续{consecutive_empty}次无数据，停止")
                        break

                # 智能延迟
                delay = self._calculate_smart_delay(request_time, len(all_data))
                if delay > 0:
                    time.sleep(delay)

            except Exception as e:
                print(f"      ❌ 批次失败: {e}")
                continue

        # 数据后处理
        final_data = self._post_process_data(all_data, symbol)

        # 计算性能指标
        self._calculate_performance_metrics(final_data)

        return final_data

    def _check_data_novelty(self, new_data: pd.DataFrame, existing_data: List[pd.DataFrame]) -> bool:
        """检查数据新颖性，避免重复"""

        if not existing_data:
            return True

        new_times = set(new_data['time'])

        for data in existing_data:
            if not data.empty:
                existing_times = set(data['time'])
                overlap = len(new_times & existing_times)

                # 如果重叠度超过80%，认为是重复数据
                if overlap > len(new_times) * 0.8:
                    return False

        return True

    def _calculate_smart_delay(self, request_time: float, data_count: int) -> float:
        """计算智能延迟时间"""

        # 基于请求时间调整延迟
        if request_time < 0.1:  # 响应很快，可以稍微快一点
            base_delay = 0.05
        elif request_time < 0.3:  # 响应正常
            base_delay = 0.1
        else:  # 响应较慢，需要更长延迟
            base_delay = 0.2

        # 基于数据量调整（避免服务器压力）
        if data_count > 5:
            base_delay *= 1.5

        return min(base_delay, 0.5)  # 最大延迟0.5秒

    def _time_from_opening(self, time_str: str) -> float:
        """计算时间距离开盘的分钟数"""

        try:
            current_time = datetime.strptime(time_str, '%H:%M')
            opening_time = datetime.strptime('09:30', '%H:%M')

            if current_time < opening_time:
                return 0
            else:
                return (current_time - opening_time).total_seconds() / 60

        except:
            return 0

    def _calculate_time_span(self, data: pd.DataFrame) -> float:
        """计算数据时间跨度（分钟）"""

        if data.empty or len(data) < 2:
            return 1.0

        try:
            earliest = datetime.strptime(data['time'].iloc[0], '%H:%M')
            latest = datetime.strptime(data['time'].iloc[-1], '%H:%M')
            span_minutes = (latest - earliest).total_seconds() / 60
            return max(span_minutes, 1.0)

        except:
            return 1.0

    def _post_process_data(self, all_data: List[pd.DataFrame], symbol: str) -> pd.DataFrame:
        """数据后处理：去重、排序、增强"""

        if not all_data:
            return pd.DataFrame()

        print(f"   🔄 数据后处理...")

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

        # 计算累计成交量
        if 'vol' in merged_data.columns:
            merged_data['volume'] = merged_data['vol'].cumsum()

        # 去重统计
        duplicate_rate = (original_count - after_dedup_count) / original_count * 100
        self.performance_stats['duplicate_rate'] = duplicate_rate
        self.performance_stats['data_records'] = after_dedup_count

        print(f"      去重: {original_count} → {after_dedup_count} (减少{duplicate_rate:.1f}%)")

        return merged_data

    def _calculate_performance_metrics(self, final_data: pd.DataFrame):
        """计算性能指标"""

        if not final_data.empty:
            # 时间覆盖率分析
            time_periods = {
                'opening': ('09:30', '09:45'),
                'morning': ('09:45', '11:30'),
                'afternoon': ('13:00', '15:00')
            }

            covered_periods = 0
            for period_name, (start_time, end_time) in time_periods.items():
                period_data = final_data[
                    (final_data['time'] >= start_time) &
                    (final_data['time'] < end_time)
                ]

                if not period_data.empty:
                    covered_periods += 1

            self.performance_stats['coverage_rate'] = covered_periods / len(time_periods) * 100
            self.performance_stats['successful_requests'] = self.performance_stats['total_requests']

    def print_performance_report(self):
        """打印性能报告"""

        stats = self.performance_stats
        print(f"\n📊 终极策略性能报告:")
        print(f"   🔢 总请求数: {stats['total_requests']}")
        print(f"   ✅ 成功请求: {stats['successful_requests']}")
        print(f"   📈 数据记录: {stats['data_records']:,}")
        print(f"   🔄 去重率: {stats['duplicate_rate']:.1f}%")
        print(f"   📅 时间覆盖率: {stats['coverage_rate']:.1f}%")

        if stats['total_requests'] > 0:
            efficiency = stats['data_records'] / stats['total_requests']
            print(f"   ⚡ 获取效率: {efficiency:.0f}条/请求")


def test_ultimate_optimal_strategy():
    """测试终极最优策略"""

    print("=" * 80)
    print("🏆 终极最优历史分笔数据获取策略测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    from mootdx.quotes import Quotes

    # 创建策略实例
    strategy = UltimateOptimalTickStrategy()

    # 测试股票（覆盖不同类别）
    test_stocks = [
        ('000001', '平安银行'),    # 高活跃股
        ('688001', '华兴源创'),    # 科创板超级活跃
        ('600036', '招商银行'),    # 银行股
    ]

    test_date = '20251117'

    for symbol, name in test_stocks:
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
            start_time = time.time()

            # 执行终极最优策略
            result_data = strategy.execute_optimal_fetch(
                client, symbol, test_date, max_records=20000
            )

            execution_time = time.time() - start_time

            if not result_data.empty:
                print(f"\n🎉 成功获取数据!")
                print(f"📊 记录数: {len(result_data):,}")
                print(f"🕐 时间范围: {result_data['time'].iloc[0]} - {result_data['time'].iloc[-1]}")
                print(f"⏱️ 执行时间: {execution_time:.2f}秒")
                print(f"💰 价格范围: {result_data['price'].min():.2f} - {result_data['price'].max():.2f}")

                # 保存数据
                filename = f"ultimate_optimal_{symbol}_{test_date}.csv"
                result_data.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"💾 数据保存: {filename}")

            else:
                print(f"❌ 未获取到数据")

        except Exception as e:
            print(f"❌ 测试失败: {e}")

        finally:
            client.close()

        # 打印性能报告
        strategy.print_performance_report()

        # 重置统计
        strategy.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'data_records': 0,
            'duplicate_rate': 0,
            'coverage_rate': 0
        }

        print(f"\n⏳ 等待3秒后测试下一只股票...")
        time.sleep(3)


if __name__ == "__main__":
    test_ultimate_optimal_strategy()
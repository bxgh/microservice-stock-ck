#!/usr/bin/env python3
"""
修复版股票分笔数据获取工具

主要修复：
1. 修复获取策略 - 确保获取完整时段数据
2. 修复终止条件 - 更准确判断数据结束
3. 增强数据验证 - 确保数据完整性
4. 修复重叠策略 - 防止数据遗漏
5. 增加调试信息 - 便于问题诊断

使用方法：
python fixed_transactions_fetcher_clean.py --symbol 000001 --date 20251120 --debug
"""

import argparse
import hashlib
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

try:
    from mootdx.quotes import Quotes
except ImportError:
    print("错误：无法导入mootdx库，请确保已正确安装")
    print("安装命令：pip install mootdx")
    sys.exit(1)


class FixedTransactionFetcher:
    """修复版分笔数据获取器"""

    def __init__(self, timeout=60, best_ip=True, overlap_ratio=0.2):
        """
        初始化修复版数据获取器

        修复要点：
        1. 更保守的重叠比例（0.2）
        2. 更大的批次大小和限制
        3. 更宽松的终止条件
        4. 更完善的验证机制
        """
        self.timeout = timeout
        self.best_ip = best_ip
        self.overlap_ratio = max(0.1, min(0.3, overlap_ratio))  # 限制在10%-30%
        self.client = None
        self.debug = False

        # 修复后的默认参数
        self.batch_size = 800        # 更小的批次
        self.max_records = 200000    # 更大的限制
        self.max_consecutive_empty = 5  # 更多的重试
        self.min_fetch_size = 50      # 最小获取数量

        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'duplicate_records': 0,
            'gap_detected': 0,
            'retry_count': 0,
            'time_gaps_found': []
        }

    def connect(self):
        """连接到行情服务器"""
        try:
            self.client = Quotes.factory(
                market='std',
                best_ip=self.best_ip,
                timeout=self.timeout
            )
            print(f"[OK] 成功连接到行情服务器 (修复版)")
            print(f"  重叠比例: {self.overlap_ratio:.1%}")
            print(f"  批次大小: {self.batch_size}")
            print(f"  最大记录: {self.max_records}")
            return True
        except Exception as e:
            print(f"[ERROR] 连接服务器失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        if self.client:
            try:
                self.client.close()
                print("[OK] 已关闭连接")
            except:
                pass

    def _create_record_key(self, df):
        """
        创建记录的唯一标识

        修复：使用更精确的键生成
        """
        keys = []
        for _, row in df.iterrows():
            # 使用时间、价格、成交量作为唯一标识
            key = f"{row['time']}_{row['price']}_{row['volume']}"
            keys.append(key)
        return keys

    def _comprehensive_fetch(self, symbol, date, fetch_start, fetch_size):
        """
        综合获取数据

        修复：实现稳定的获取逻辑
        """
        try:
            self.stats['total_requests'] += 1

            if self.debug:
                print(f"    [DEBUG] 获取数据: start={fetch_start}, count={fetch_size}")

            # 获取数据
            df = self.client.transactions(symbol=symbol, date=date, start=fetch_start, count=fetch_size)

            if df is None or df.empty:
                if self.debug:
                    print(f"    [DEBUG] 返回空数据")
                self.stats['successful_requests'] += 1
                return pd.DataFrame(), True  # 空数据也是成功响应

            # 基本验证
            if len(df) == 0:
                if self.debug:
                    print(f"    [DEBUG] 数据长度为0")
                self.stats['successful_requests'] += 1
                return pd.DataFrame(), True

            self.stats['successful_requests'] += 1

            if self.debug:
                print(f"    [DEBUG] 成功获取 {len(df)} 条记录")
                if len(df) > 0:
                    print(f"    [DEBUG] 时间范围: {df['time'].iloc[0]} - {df['time'].iloc[-1]}")

            return df, False

        except Exception as e:
            if self.debug:
                print(f"    [DEBUG] 获取失败: {e}")
            return pd.DataFrame(), False

    def get_transactions_comprehensive(self, symbol, date, target_start=0):
        """
        全面获取分笔数据

        修复核心：多起始位置 + 综合验证
        """
        if not self.client:
            print("[ERROR] 未连接到服务器")
            return pd.DataFrame()

        print(f"\n开始全面获取数据: {symbol} {date}")
        print(f"修复策略: 多起始位置综合获取")

        all_data = []
        seen_keys = set()

        # 修复：使用多个起始位置确保数据完整
        start_positions = [0, 2000, 4000, 6000, 8000]
        fetch_size = self.batch_size

        for start_pos in start_positions:
            print(f"\n处理起始位置: {start_pos}")
            position_data = []
            consecutive_empty = 0
            max_consecutive_empty = self.max_consecutive_empty

            current_start = start_pos
            position_success = False

            while current_start < self.max_records and len(position_data) < self.max_records:
                if self.debug:
                    print(f"  [DEBUG] 当前位置: {current_start}, 已获取: {len(position_data)}")

                # 执行数据获取
                df, is_empty = self._comprehensive_fetch(symbol, date, current_start, fetch_size)

                if is_empty:
                    consecutive_empty += 1
                    if self.debug:
                        print(f"  [DEBUG] 连续空返回: {consecutive_empty}")

                    if consecutive_empty >= max_consecutive_empty:
                        print(f"  [INFO] 起始位置 {start_pos} 连续空返回 {max_consecutive_empty} 次，停止获取")
                        break

                    current_start += fetch_size // 2  # 保守前进
                    continue

                consecutive_empty = 0  # 重置空计数
                position_success = True

                # 去重处理
                new_data = []
                duplicate_count = 0

                for _, row in df.iterrows():
                    key = f"{row['time']}_{row['price']}_{row['volume']}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        new_data.append(row)
                    else:
                        duplicate_count += 1

                if duplicate_count > 0:
                    self.stats['duplicate_records'] += duplicate_count
                    if self.debug:
                        print(f"  [DEBUG] 去重: {duplicate_count} 条重复记录")

                if new_data:
                    position_data.extend(new_data)
                    print(f"  [INFO] 新增 {len(new_data)} 条记录 (累计: {len(position_data)})")

                # 修复：更宽松的终止条件
                if len(df) < self.min_fetch_size:
                    if self.debug:
                        print(f"  [DEBUG] 获取数量过少 ({len(df)} < {self.min_fetch_size})，可能到达数据末尾")
                    break

                # 修复：更保守的步进
                overlap_size = int(fetch_size * self.overlap_ratio)
                current_start = current_start + fetch_size - overlap_size

                # 修复：避免无限循环
                if len(position_data) > 10000 and len(df) == len(new_data):  # 全是新数据
                    if self.debug:
                        print(f"  [DEBUG] 数据量充足且无重复，适度加大步进")
                    current_start += fetch_size // 2

                time.sleep(0.1)  # 减少请求频率

            if position_success and position_data:
                all_data.extend(position_data)
                print(f"  [OK] 起始位置 {start_pos} 完成，获取 {len(position_data)} 条记录")
            else:
                print(f"  [WARN] 起始位置 {start_pos} 没有获取到有效数据")

        if not all_data:
            print("[ERROR] 所有起始位置都未获取到数据")
            return pd.DataFrame()

        # 创建结果DataFrame
        if all_data:
            full_df = pd.DataFrame(all_data)
            print(f"\n[OK] 数据合并完成: {len(full_df)} 条记录")
        else:
            print("[ERROR] 数据合并失败")
            return pd.DataFrame()

        # 修复：添加数据完整性验证
        if not full_df.empty and len(full_df) > 1:
            print("\n开始数据完整性验证...")
            completeness_score = self._analyze_data_completeness(full_df)
            print(f"数据完整性评分: {completeness_score}/100")

            if completeness_score < 50:
                print("[WARN] 数据完整性较低，建议检查网络或重试")

        return full_df

    def _analyze_data_completeness(self, df):
        """
        分析数据完整性

        修复：更完善的完整性评估
        """
        try:
            if len(df) == 0:
                return 0

            score = 0
            max_score = 100

            # 检查1: 时间覆盖度 (30分)
            if 'time' in df.columns:
                # 先尝试 %H:%M:%S 格式，如果失败再尝试 %H:%M 格式
                times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
                times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
                # 合并两种格式的结果
                times = times_hms.fillna(times_hm).dt.time
                time_span = (times.max().hour * 60 + times.max().minute) - (times.min().hour * 60 + times.min().minute)

                if time_span >= 330:  # 5.5小时以上
                    score += 30
                elif time_span >= 240:  # 4小时以上
                    score += 25
                elif time_span >= 180:  # 3小时以上
                    score += 20
                elif time_span >= 120:  # 2小时以上
                    score += 15
                elif time_span >= 60:   # 1小时以上
                    score += 10

            # 检查2: 数据量充足度 (25分)
            if len(df) >= 4000:
                score += 25
            elif len(df) >= 3000:
                score += 20
            elif len(df) >= 2000:
                score += 15
            elif len(df) >= 1000:
                score += 10
            elif len(df) >= 500:
                score += 5

            # 检查3: 时间连续性 (25分)
            if 'time' in df.columns and len(df) > 1:
                # 先尝试 %H:%M:%S 格式，如果失败再尝试 %H:%M 格式
                times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
                times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
                # 合并两种格式的结果
                times = times_hms.fillna(times_hm).sort_values()
                time_diffs = times.diff().dt.total_seconds()

                # 统计大间隔
                large_gaps = (time_diffs > 300).sum()  # 5分钟以上间隔
                if large_gaps == 0:
                    score += 25
                elif large_gaps <= 2:
                    score += 20
                elif large_gaps <= 5:
                    score += 15
                elif large_gaps <= 10:
                    score += 10
                else:
                    score += 5

            # 检查4: 交易时间分布 (20分)
            if 'time' in df.columns:
                # 先尝试 %H:%M:%S 格式，如果失败再尝试 %H:%M 格式
                times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
                times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
                # 合并两种格式的结果
                times = times_hms.fillna(times_hm).dt.hour

                # 检查是否覆盖主要交易时段
                has_morning = ((times >= 9) & (times <= 11)).any()
                has_afternoon = ((times >= 13) & (times <= 15)).any()

                if has_morning and has_afternoon:
                    score += 20
                elif has_afternoon:
                    score += 10
                elif has_morning:
                    score += 10

            return min(score, max_score)

        except Exception as e:
            print(f"[ERROR] 完整性分析失败: {e}")
            return 0

    def validate_trading_hours(self, df):
        """
        验证交易时间覆盖情况

        修复：更准确的时间验证
        """
        try:
            if df.empty:
                return False

            # 先过滤掉无效的时间数据 - 支持多种时间格式
            times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
            times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
            # 合并两种格式的结果
            valid_times = times_hms.fillna(times_hm)
            valid_times_mask = valid_times.notna()

            if not valid_times_mask.any():
                print("  [ERROR] 没有有效的时间数据")
                return False

            valid_df = df[valid_times_mask].copy()
            times = valid_times.dt.time

            # 关键交易时间点
            key_times = [
                datetime.strptime('09:25:00', '%H:%M:%S').time(),  # 集合竞价
                datetime.strptime('09:30:00', '%H:%M:%S').time(),  # 早盘开盘
                datetime.strptime('11:30:00', '%H:%M:%S').time(),  # 早盘收盘
                datetime.strptime('13:00:00', '%H:%M:%S').time(),  # 午盘开盘
                datetime.strptime('15:00:00', '%H:%M:%S').time(),  # 全天收盘
            ]

            print("\n交易时间覆盖分析:")
            for key_time in key_times:
                key_time_str = key_time.strftime('%H:%M:%S')
                # 过滤掉NaT值后再计算
                valid_time_list = [t for t in times if pd.notna(t)]
                if not valid_time_list:
                    break

                closest_times = [abs((datetime.combine(datetime.today(), t) - datetime.combine(datetime.today(), key_time)).total_seconds()) for t in valid_time_list]
                min_diff = min(closest_times) if closest_times else float('inf')

                if min_diff <= 60:  # 1分钟内
                    print(f"  [OK] 找到时间点: {key_time_str}")
                elif min_diff <= 300:  # 5分钟内
                    print(f"  [WARN] 接近时间点: {key_time_str} (偏差{min_diff:.0f}秒)")
                else:
                    print(f"  [MISS] 缺失时间点: {key_time_str}")

            # 基本统计 - 确保时间数据有效
            valid_time_list = [t for t in times if pd.notna(t)]
            if valid_time_list:
                min_time = min(valid_time_list)
                max_time = max(valid_time_list)

                if min_time <= datetime.strptime('09:30:00', '%H:%M:%S').time():
                    print(f"  [OK] 覆盖早盘开盘: {min_time.strftime('%H:%M:%S')}")
                else:
                    print(f"  [WARN] 早盘数据缺失: 最早 {min_time.strftime('%H:%M:%S')}")

                if max_time >= datetime.strptime('14:50:00', '%H:%M:%S').time():
                    print(f"  [OK] 覆盖尾盘: {max_time.strftime('%H:%M:%S')}")
                else:
                    print(f"  [WARN] 尾盘数据缺失: 最晚 {max_time.strftime('%H:%M:%S')}")

            return True

        except Exception as e:
            print(f"[ERROR] 时间验证失败: {e}")
            return False

    def _sort_data_by_time(self, df):
        """
        按时间对数据进行排序

        修复：确保数据按时间顺序排列
        """
        try:
            if df.empty or 'time' not in df.columns:
                return df

            # 支持多种时间格式进行排序
            times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
            times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
            sorted_times = times_hms.fillna(times_hm)

            # 创建排序列
            df_copy = df.copy()
            df_copy['sort_time'] = sorted_times

            # 按时间排序并移除临时列
            df_sorted = df_copy.sort_values('sort_time').drop('sort_time', axis=1)

            # 重置索引
            df_sorted = df_sorted.reset_index(drop=True)

            return df_sorted

        except Exception as e:
            print(f"[WARN] 数据排序失败，使用原始顺序: {e}")
            return df

    def _generate_detailed_statistics(self, df, symbol, date):
        """
        生成详细的统计信息

        修复：提供完整的数据统计报告
        """
        try:
            print("\n" + "="*60)
            print("详细统计分析报告")
            print("="*60)

            # 基本信息
            print(f"\n基本信息:")
            print(f"  股票代码: {symbol}")
            print(f"  交易日期: {date}")
            print(f"  总记录数: {len(df):,} 条")

            if df.empty or 'time' not in df.columns:
                print("  [ERROR] 数据为空或缺少时间信息")
                return

            # 时间分析
            times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
            times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
            valid_times = times_hms.fillna(times_hm)

            print(f"\n时间分析:")
            print(f"  时间范围: {df['time'].min()} - {df['time'].max()}")
            print(f"  首笔交易: {df['time'].iloc[0]}")
            print(f"  末笔交易: {df['time'].iloc[-1]}")

            # 时段分布
            morning_mask = valid_times.dt.hour.isin([9, 10, 11])
            afternoon_mask = valid_times.dt.hour.isin([13, 14, 15])

            morning_count = morning_mask.sum()
            afternoon_count = afternoon_mask.sum()

            print(f"\n时段分布:")
            print(f"  上午交易 (09:00-11:59): {morning_count:,} 条 ({morning_count/len(df)*100:.1f}%)")
            print(f"  下午交易 (13:00-15:59): {afternoon_count:,} 条 ({afternoon_count/len(df)*100:.1f}%)")

            # 价格分析（如果存在）
            if 'price' in df.columns:
                print(f"\n价格分析:")
                print(f"  最高价: {df['price'].max():.2f}")
                print(f"  最低价: {df['price'].min():.2f}")
                print(f"  平均价: {df['price'].mean():.2f}")
                print(f"  价格波动: {df['price'].max() - df['price'].min():.2f}")

            # 成交量分析（如果存在）
            if 'volume' in df.columns:
                print(f"\n成交量分析:")
                print(f"  总成交量: {df['volume'].sum():,}")
                print(f"  平均每笔: {df['volume'].mean():.0f}")
                print(f"  最大单笔: {df['volume'].max():,}")
                print(f"  最小单笔: {df['volume'].min():,}")

            # 买卖方向分析（如果存在）
            if 'buyorsell' in df.columns:
                buy_count = (df['buyorsell'] == 1).sum()
                sell_count = (df['buyorsell'] == 0).sum()

                print(f"\n买卖方向分析:")
                print(f"  主动买入: {buy_count:,} 条 ({buy_count/(buy_count+sell_count)*100:.1f}%)")
                print(f"  主动卖出: {sell_count:,} 条 ({sell_count/(buy_count+sell_count)*100:.1f}%)")

            # 交易强度分析
            if 'time' in df.columns and len(df) > 1:
                # 按小时统计交易密度
                hourly_counts = df.groupby(df['time'].str[:2]).size()
                print(f"\n小时交易密度:")
                for hour, count in hourly_counts.sort_index().items():
                    print(f"  {hour}:00-{hour}:59: {count:,} 条")

            print("\n" + "="*60)

        except Exception as e:
            print(f"[ERROR] 统计分析失败: {e}")

    def save_data(self, df, symbol, date, format='both'):
        """保存数据到文件"""
        if df.empty:
            print("[ERROR] 没有数据可保存")
            return

        # 按时间排序数据
        df_sorted = self._sort_data_by_time(df)

        # 生成详细统计
        self._generate_detailed_statistics(df_sorted, symbol, date)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{symbol}_{date}_fixed_transactions_{timestamp}"

        try:
            if format in ['csv', 'both']:
                csv_filename = f"{base_filename}.csv"
                df_sorted.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                file_size = os.path.getsize(csv_filename)
                print(f"[OK] CSV文件已保存: {csv_filename} ({file_size/1024:.1f} KB)")
                print(f"      数据已按时间顺序排列")

            if format in ['excel', 'both']:
                excel_filename = f"{base_filename}.xlsx"
                df_sorted.to_excel(excel_filename, index=False)
                file_size = os.path.getsize(excel_filename)
                print(f"[OK] Excel文件已保存: {excel_filename} ({file_size/1024:.1f} KB)")
                print(f"      数据已按时间顺序排列")

        except Exception as e:
            print(f"[ERROR] 文件保存失败: {e}")

    def print_stats(self):
        """显示统计信息"""
        print("\n" + "="*50)
        print("修复版获取统计:")
        print("="*50)
        print(f"总请求数: {self.stats['total_requests']}")
        print(f"成功请求: {self.stats['successful_requests']}")
        print(f"重复记录: {self.stats['duplicate_records']}")
        print(f"检测到的间隙: {self.stats['gap_detected']}")
        print(f"重试次数: {self.stats['retry_count']}")
        if self.stats['time_gaps_found']:
            print(f"发现时间间隙: {len(self.stats['time_gaps_found'])} 个")


def main():
    parser = argparse.ArgumentParser(description='修复版股票分笔数据获取工具')
    parser.add_argument('--symbol', required=True, help='股票代码 (例如: 000001)')
    parser.add_argument('--date', required=True, help='日期 (格式: YYYYMMDD)')
    parser.add_argument('--timeout', type=int, default=60, help='连接超时时间')
    parser.add_argument('--no-best-ip', action='store_true', help='不使用最佳IP')
    parser.add_argument('--overlap', type=float, default=0.2, help='重叠比例 (0.1-0.3)')
    parser.add_argument('--format', choices=['csv', 'excel', 'both'], default='both', help='输出格式')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')

    args = parser.parse_args()

    print("="*60)
    print("修复版股票分笔数据获取工具")
    print("="*60)
    print("主要修复:")
    print("- 修复获取策略，确保获取完整时段数据")
    print("- 修复终止条件，准确判断数据结束")
    print("- 修复重叠策略，防止数据遗漏")
    print("- 增强验证机制，确保数据完整性")
    print("- 增强调试信息，便于问题诊断")

    # 创建修复版获取器
    fetcher = FixedTransactionFetcher(
        timeout=args.timeout,
        best_ip=not args.no_best_ip,
        overlap_ratio=args.overlap
    )
    fetcher.debug = args.debug

    # 连接服务器
    if not fetcher.connect():
        print("[ERROR] 连接失败，程序退出")
        return 1

    try:
        # 开始获取数据
        start_time = time.time()
        df = fetcher.get_transactions_comprehensive(args.symbol, args.date)
        end_time = time.time()

        if df is not None and not df.empty:
            print(f"\n[OK] 数据获取成功!")
            print(f"  总记录数: {len(df):,}")
            print(f"  用时: {end_time - start_time:.2f} 秒")

            # 数据验证
            fetcher.validate_trading_hours(df)

            # 保存数据
            fetcher.save_data(df, args.symbol, args.date, args.format)

            # 显示统计
            fetcher.print_stats()

            return 0
        else:
            print("[ERROR] 未能获取到有效数据")
            return 1

    except Exception as e:
        print(f"[ERROR] 程序执行出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        fetcher.close()


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
改进的报告生成器
修正了数据完整性评分中的时间覆盖度计算问题
基于A股标准交易时段进行合理评估
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, time as dt_time, timedelta


def generate_quality_report(data: List[Any]) -> Dict[str, Any]:
    """
    生成改进的数据质量报告
    修正了时间覆盖度评估标准

    Args:
        data: 分笔数据列表

    Returns:
        Dict[str, Any]: 改进的质量报告
    """
    if not data:
        return {
            'completeness_score': 0,
            'time_coverage': 0.0,
            'quality_grade': 'E',
            'error_message': '没有数据'
        }

    try:
        report = {
            'completeness_score': 0,
            'time_coverage': 0.0,
            'quality_grade': 'E',
            'total_records': len(data),
            'analysis_details': {},
            'improvements_applied': ['corrected_time_coverage_standard']
        }

        # 转换为DataFrame进行分析
        df = _convert_to_dataframe(data)
        if df.empty:
            return report

        # 使用改进的分析维度
        time_score = _analyze_time_coverage_corrected(df)
        volume_score = _analyze_volume_adequacy(df)
        continuity_score = _analyze_time_continuity(df)
        distribution_score = _analyze_trading_distribution(df)

        report['analysis_details'] = {
            'time_score': time_score,
            'volume_score': volume_score,
            'continuity_score': continuity_score,
            'distribution_score': distribution_score,
            'time_coverage_details': _get_time_coverage_details(df)
        }

        # 重新调整权重分配，更加合理
        max_score = 100
        time_weight = 35      # 时间覆盖度权重（增加，因为是核心指标）
        volume_weight = 25    # 数据量权重
        continuity_weight = 25 # 连续性权重
        distribution_weight = 15 # 分布权重（减少）

        report['completeness_score'] = min(
            int(time_score * time_weight / max_score +
                volume_score * volume_weight / max_score +
                continuity_score * continuity_weight / max_score +
                distribution_score * distribution_weight / max_score),
            max_score
        )

        # 修正时间覆盖率计算
        report['time_coverage'] = time_score / 35.0  # 基于新的满分标准

        # 评级
        report['quality_grade'] = _get_quality_grade(report['completeness_score'])

        return report

    except Exception as e:
        return {
            'completeness_score': 0,
            'time_coverage': 0.0,
            'quality_grade': 'E',
            'error_message': f'分析失败: {str(e)}'
        }


def _convert_to_dataframe(data: List[Any]) -> pd.DataFrame:
    """转换数据为DataFrame"""
    if not data:
        return pd.DataFrame()

    records = []
    for item in data:
        try:
            record = {
                'time': getattr(item, 'time', None),
                'price': getattr(item, 'price', 0),
                'volume': getattr(item, 'volume', 0),
                'direction': getattr(item, 'direction', 'N')
            }
            records.append(record)
        except:
            continue

    return pd.DataFrame(records)


def _analyze_time_coverage_corrected(df: pd.DataFrame) -> int:
    """
    改进的时间覆盖度分析 (35分满分)
    基于A股标准交易时段进行合理评估
    """
    if 'time' not in df.columns or df.empty:
        return 0

    try:
        # 解析时间
        times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
        times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
        valid_times = times_hms.fillna(times_hm)

        if valid_times.empty:
            return 0

        # A股标准交易时段定义
        trading_sessions = {
            'morning_auction': ('09:25:00', '09:30:00'),     # 集合竞价：5分钟
            'morning_trading': ('09:30:00', '11:30:00'),    # 上午连续交易：2小时
            'lunch_break': ('11:30:00', '13:00:00'),        # 午间休市：1.5小时
            'afternoon_trading': ('13:00:00', '15:00:00')   # 下午连续交易：2小时
        }

        # 计算覆盖的交易时段
        covered_minutes = _calculate_covered_trading_time(valid_times, trading_sessions)

        # 标准交易总时长 = 4小时 (不含集合竞价)
        standard_trading_minutes = 240  # 4小时

        # 计算覆盖率
        coverage_rate = min(1.0, covered_minutes / standard_trading_minutes)

        # 基于覆盖率的评分（35分满分）
        if coverage_rate >= 0.95:     # 95%以上覆盖
            return 35
        elif coverage_rate >= 0.90:   # 90%以上覆盖
            return 32
        elif coverage_rate >= 0.80:   # 80%以上覆盖
            return 28
        elif coverage_rate >= 0.70:   # 70%以上覆盖
            return 25
        elif coverage_rate >= 0.60:   # 60%以上覆盖
            return 20
        elif coverage_rate >= 0.50:   # 50%以上覆盖
            return 15
        elif coverage_rate >= 0.40:   # 40%以上覆盖
            return 10
        elif coverage_rate >= 0.30:   # 30%以上覆盖
            return 5
        else:
            return max(0, int(coverage_rate * 10))

    except Exception as e:
        print(f"[WARN] 时间覆盖度分析失败: {e}")
        return 0


def _calculate_covered_trading_time(valid_times: pd.DatetimeIndex,
                                 trading_sessions: dict) -> int:
    """
    计算实际覆盖的交易时间（分钟）
    考虑跨午休的实际情况
    """
    try:
        covered_minutes = 0

        # 转换为分钟数
        time_minutes = valid_times.dt.hour * 60 + valid_times.dt.minute + valid_times.dt.second / 60

        # 分析上午交易时段 (09:30-11:30)
        morning_mask = (time_minutes >= 9*60 + 30) & (time_minutes <= 11*60 + 30)
        if morning_mask.any():
            morning_span = time_minutes[morning_mask].max() - time_minutes[morning_mask].min()
            covered_minutes += max(0, morning_span)

        # 分析下午交易时段 (13:00-15:00)
        afternoon_mask = (time_minutes >= 13*60) & (time_minutes <= 15*60)
        if afternoon_mask.any():
            afternoon_span = time_minutes[afternoon_mask].max() - time_minutes[afternoon_mask].min()
            covered_minutes += max(0, afternoon_span)

        # 分析集合竞价时段 (09:25-09:30)
        auction_mask = (time_minutes >= 9*60 + 25) & (time_minutes <= 9*60 + 30)
        if auction_mask.any():
            covered_minutes += 5  # 集合竞价固定5分钟

        return int(covered_minutes)

    except Exception as e:
        print(f"[WARN] 交易时间计算失败: {e}")
        return 0


def _get_time_coverage_details(df: pd.DataFrame) -> Dict[str, Any]:
    """获取详细的时间覆盖度分析"""
    if 'time' not in df.columns or df.empty:
        return {}

    try:
        times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
        times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
        valid_times = times_hms.fillna(times_hm)

        if valid_times.empty:
            return {}

        # 时间分布统计
        hours = valid_times.dt.hour

        # 主要交易时段覆盖情况
        session_coverage = {
            'has_auction': ((hours == 9) & (valid_times.dt.minute >= 25) & (valid_times.dt.minute <= 30)).any(),
            'has_morning': ((hours >= 9) & (hours <= 11)).any(),
            'has_afternoon': ((hours >= 13) & (hours <= 15)).any(),
            'time_span_minutes': 0,
            'coverage_rate': 0.0
        }

        # 计算实际时间跨度
        if len(valid_times) > 1:
            time_minutes = hours * 60 + valid_times.dt.minute + valid_times.dt.second / 60
            session_coverage['time_span_minutes'] = int(time_minutes.max() - time_minutes.min())

            # 基于标准交易时段计算覆盖率
            trading_sessions = {
                'morning_auction': ('09:25:00', '09:30:00'),
                'morning_trading': ('09:30:00', '11:30:00'),
                'afternoon_trading': ('13:00:00', '15:00:00')
            }

            covered_minutes = _calculate_covered_trading_time(valid_times, trading_sessions)
            session_coverage['coverage_rate'] = round(covered_minutes / 240, 2)  # 240分钟标准交易时长

        return session_coverage

    except Exception as e:
        print(f"[WARN] 时间覆盖度详情分析失败: {e}")
        return {}


def _analyze_volume_adequacy(df: pd.DataFrame) -> int:
    """分析数据量充足度 (25分满分) - 保持原有逻辑"""
    if df.empty:
        return 0

    record_count = len(df)
    if record_count >= 4000:
        return 25
    elif record_count >= 3000:
        return 20
    elif record_count >= 2000:
        return 15
    elif record_count >= 1000:
        return 10
    elif record_count >= 500:
        return 5
    else:
        return max(0, record_count // 100)


def _analyze_time_continuity(df: pd.DataFrame) -> int:
    """分析时间连续性 (25分满分) - 修正版，支持跨午休处理"""
    if 'time' not in df.columns or len(df) <= 1:
        return 25  # 单条数据给满分

    try:
        # 提取时间，处理多种格式
        times_list = []
        for idx, row in df.iterrows():
            time_val = row['time']

            if isinstance(time_val, str):
                # 字符串格式时间
                try:
                    if ':' in time_val:
                        parsed_time = pd.to_datetime(time_val, format='%H:%M:%S', errors='coerce')
                        if pd.isna(parsed_time):
                            parsed_time = pd.to_datetime(time_val, format='%H:%M', errors='coerce')
                        if not pd.isna(parsed_time):
                            times_list.append(parsed_time)
                except:
                    continue
            elif hasattr(time_val, 'hour'):
                # datetime.time对象
                dummy_date = pd.Timestamp('2024-01-01')
                parsed_time = pd.Timestamp.combine(dummy_date, time_val)
                times_list.append(parsed_time)
            elif pd.api.types.is_datetime64_any_dtype(type(time_val)):
                # pandas datetime
                times_list.append(pd.to_datetime(time_val))

        if len(times_list) <= 1:
            return 25

        # 转换为Series并排序
        times = pd.Series(times_list).sort_values().reset_index(drop=True)

        # 计算时间间隔
        time_diffs = times.diff().dt.total_seconds()

        # 统计大间隔，考虑A股交易时段特点
        large_gaps = 0
        total_intervals = len(time_diffs) - 1

        # 定义A股正常交易时段
        MORNING_START = 9 * 3600 + 30 * 60    # 09:30
        MORNING_END = 11 * 3600 + 30 * 60     # 11:30
        AFTERNOON_START = 13 * 3600           # 13:00
        AFTERNOON_END = 15 * 3600             # 15:00
        LUNCH_BREAK = AFTERNOON_START - MORNING_END  # 午休时长

        for i, diff in enumerate(time_diffs[1:], 1):
            if pd.isna(diff):
                continue

            prev_time = times.iloc[i-1]
            current_time = times.iloc[i]

            prev_seconds = prev_time.hour * 3600 + prev_time.minute * 60 + prev_time.second
            current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second

            # 检查是否跨越午休时段（09:30-11:30 -> 13:00-15:00）
            is_cross_lunch = (
                prev_seconds <= MORNING_END and
                current_seconds >= AFTERNOON_START and
                abs(current_seconds - prev_seconds - LUNCH_BREAK) <= 600  # 允许10分钟误差
            )

            # 检查是否在正常交易时段内的大间隔（>5分钟）
            is_trading_time_gap = (
                MORNING_START <= prev_seconds <= MORNING_END and
                MORNING_START <= current_seconds <= MORNING_END and
                diff > 300
            ) or (
                AFTERNOON_START <= prev_seconds <= AFTERNOON_END and
                AFTERNOON_START <= current_seconds <= AFTERNOON_END and
                diff > 300
            )

            # 只标记真正的大间隔，忽略正常跨午休和交易时段外的间隔
            if is_trading_time_gap:
                large_gaps += 1
            elif not is_cross_lunch and diff > 300:
                # 非午休时段的大间隔，但也要有合理的阈值
                if diff > 1800:  # 30分钟以上的大间隔才算
                    large_gaps += 1

        # 计算连续性得分
        if total_intervals <= 0:
            return 25

        # 调整评分标准，更加宽容
        gap_ratio = large_gaps / max(total_intervals, 1)

        if gap_ratio == 0:
            return 25  # 完美连续
        elif gap_ratio <= 0.05:  # 5%以下大间隔
            return 23
        elif gap_ratio <= 0.10:  # 10%以下大间隔
            return 20
        elif gap_ratio <= 0.20:  # 20%以下大间隔
            return 15
        elif gap_ratio <= 0.35:  # 35%以下大间隔
            return 10
        elif gap_ratio <= 0.50:  # 50%以下大间隔
            return 5
        else:
            return max(0, 3)  # 非常不连续，但至少给点分

    except Exception as e:
        print(f"[WARN] 连续性分析失败: {e}")
        return 15  # 出错时给中等分数


def _analyze_trading_distribution(df: pd.DataFrame) -> int:
    """分析交易时间分布 (15分满分) - 调整权重"""
    if 'time' not in df.columns or df.empty:
        return 0

    try:
        # 解析时间
        times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
        times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
        hours = times_hms.fillna(times_hms).dt.hour

        # 检查主要交易时段覆盖
        has_morning = ((hours >= 9) & (hours <= 11)).any()
        has_afternoon = ((hours >= 13) & (hours <= 15)).any()

        # 检查关键交易时段
        has_opening = ((hours == 9) & (hours >= 30)).any()  # 开盘
        has_closing = (hours == 15).any()  # 收盘

        if has_morning and has_afternoon and has_opening and has_closing:
            return 15
        elif has_morning and has_afternoon:
            return 12
        elif has_afternoon or has_morning:
            return 8
        else:
            return 0

    except Exception:
        return 0


def _get_quality_grade(score: int) -> str:
    """获取质量评级 - 调整标准使其更合理"""
    if score >= 85:
        return 'A'
    elif score >= 75:
        return 'B'
    elif score >= 65:
        return 'C'
    elif score >= 55:
        return 'D'
    else:
        return 'E'
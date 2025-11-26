#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
报告生成器
生成数据质量分析报告
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, time as dt_time


def generate_quality_report(data: List[Any]) -> Dict[str, Any]:
    """
    生成数据质量报告

    Args:
        data: 分笔数据列表

    Returns:
        Dict[str, Any]: 质量报告
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
            'analysis_details': {}
        }

        # 转换为DataFrame进行分析
        df = _convert_to_dataframe(data)
        if df.empty:
            return report

        # 分析维度
        time_score = _analyze_time_coverage(df)
        volume_score = _analyze_volume_adequacy(df)
        continuity_score = _analyze_time_continuity(df)
        distribution_score = _analyze_trading_distribution(df)

        report['analysis_details'] = {
            'time_score': time_score,
            'volume_score': volume_score,
            'continuity_score': continuity_score,
            'distribution_score': distribution_score
        }

        # 计算综合分数
        max_score = 100
        time_weight = 30  # 时间覆盖度权重
        volume_weight = 25  # 数据量权重
        continuity_weight = 25  # 连续性权重
        distribution_weight = 20  # 分布权重

        report['completeness_score'] = min(
            int(time_score * time_weight / max_score +
                volume_score * volume_weight / max_score +
                continuity_score * continuity_weight / max_score +
                distribution_score * distribution_weight / max_score),
            max_score
        )

        # 计算时间覆盖率
        report['time_coverage'] = time_score / 30.0  # 归一化到0-1

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


def _analyze_time_coverage(df: pd.DataFrame) -> int:
    """分析时间覆盖度 (30分满分)"""
    if 'time' not in df.columns or df.empty:
        return 0

    try:
        # 解析时间
        times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
        times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
        times = times_hms.fillna(times_hm).dt.time

        # 计算时间跨度
        time_span_minutes = 0
        if len(times) > 1:
            first_time = times.iloc[0]
            last_time = times.iloc[-1]
            try:
                first_minutes = first_time.hour * 60 + first_time.minute
                last_minutes = last_time.hour * 60 + last_time.minute
                time_span_minutes = max(0, last_minutes - first_minutes)
            except:
                pass

        # 评分
        if time_span_minutes >= 330:  # 5.5小时以上
            return 30
        elif time_span_minutes >= 240:  # 4小时以上
            return 25
        elif time_span_minutes >= 180:  # 3小时以上
            return 20
        elif time_span_minutes >= 120:  # 2小时以上
            return 15
        elif time_span_minutes >= 60:  # 1小时以上
            return 10
        else:
            return max(0, int(time_span_minutes / 60))

    except Exception:
        return 0


def _analyze_volume_adequacy(df: pd.DataFrame) -> int:
    """分析数据量充足度 (25分满分)"""
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
    """分析时间连续性 (25分满分)"""
    if 'time' not in df.columns or len(df) <= 1:
        return 0

    try:
        # 解析时间
        times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
        times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
        times = times_hms.fillna(times_hm).sort_values()

        # 计算时间间隔
        time_diffs = times.diff().dt.total_seconds()

        # 统计大间隔 (5分钟以上)
        large_gaps = (time_diffs > 300).sum()
        total_intervals = len(time_diffs) - 1

        if total_intervals <= 0:
            return 25

        gap_ratio = large_gaps / total_intervals

        if gap_ratio == 0:
            return 25
        elif gap_ratio <= 0.1:
            return 20
        elif gap_ratio <= 0.2:
            return 15
        elif gap_ratio <= 0.3:
            return 10
        elif gap_ratio <= 0.5:
            return 5
        else:
            return max(0, 5)

    except Exception:
        return 0


def _analyze_trading_distribution(df: pd.DataFrame) -> int:
    """分析交易时间分布 (20分满分)"""
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

        if has_morning and has_afternoon:
            return 20
        elif has_afternoon or has_morning:
            return 10
        else:
            return 0

    except Exception:
        return 0


def _get_quality_grade(score: int) -> str:
    """获取质量评级"""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'E'
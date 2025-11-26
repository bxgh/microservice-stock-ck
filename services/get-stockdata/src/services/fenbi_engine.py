#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fenbi引擎
基于数据源抽象的新fenbi服务，保持原功能的同时提供标准化接口
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Optional
import pandas as pd

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ..data_sources.factory import DataSourceFactory
    from ..models.tick_models import TickDataRequest
    from ..utils.file_exporter import export_to_csv, export_to_excel
    from ..utils.report_generator import generate_quality_report
    from ..core.time_formatter import TimeFormatter
    from ..core.data_deduplicator import DataDeduplicator
    from ..core.statistics_generator import StatisticsGenerator
except ImportError:
    from data_sources.factory import DataSourceFactory
    from models.tick_models import TickDataRequest
    from utils.file_exporter import export_to_csv, export_to_excel
    from utils.report_generator import generate_quality_report
    from core.time_formatter import TimeFormatter
    from core.data_deduplicator import DataDeduplicator
    from core.statistics_generator import StatisticsGenerator


class FenbiEngine:
    """Fenbi数据获取引擎，基于抽象数据源"""

    def __init__(self, source_type: str = "mootdx", config: Optional[dict] = None):
        """
        初始化Fenbi引擎

        Args:
            source_type: 数据源类型
            config: 自定义配置
        """
        self.data_source = DataSourceFactory.create_source(source_type, config)

        # 初始化核心组件
        self.time_formatter = TimeFormatter()
        self.data_deduplicator = DataDeduplicator()
        self.statistics_generator = StatisticsGenerator()

        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_records': 0,
            'unique_records': 0,
            'duplicates_removed': 0,
            'success': False,
            'error_message': None
        }

    async def get_tick_data(self, symbol: str, date: str, market: str = None,
                           enable_time_sort: bool = True, enable_deduplication: bool = True) -> List:
        """
        获取分笔数据

        Args:
            symbol: 股票代码
            date: 日期字符串 (YYYYMMDD)
            market: 市场代码，如果为None则自动判断
            enable_time_sort: 是否启用时间排序
            enable_deduplication: 是否启用数据去重

        Returns:
            List: 分笔数据列表
        """
        try:
            self.stats['start_time'] = datetime.now()

            # 自动判断市场
            if market is None:
                market = 'SZ' if symbol.startswith('00') else 'SH'

            # 创建请求
            date_obj = datetime.strptime(date, '%Y%m%d')
            request = TickDataRequest(
                stock_code=symbol,
                date=date_obj,
                market=market,
                include_auction=True
            )

            # 连接数据源
            if not self.data_source.is_connected:
                if not await self.data_source.connect():
                    self.stats['error_message'] = "数据源连接失败"
                    return []

            # 获取数据
            data = await self.data_source.get_tick_data(request)

            # 数据处理管道
            if data:
                original_count = len(data)

                # 1. 时间处理和排序
                if enable_time_sort:
                    try:
                        # 转换为DataFrame进行时间排序，然后转回列表
                        df_data = []
                        for item in data:
                            record = {
                                'time': str(item.time) if hasattr(item, 'time') else '',
                                'price': float(item.price) if hasattr(item, 'price') else 0,
                                'volume': int(item.volume) if hasattr(item, 'volume') else 0,
                                'amount': float(getattr(item, 'amount', 0)),
                                'direction': str(getattr(item, 'direction', 'N')),
                                'code': str(getattr(item, 'code', '')),
                                'date': str(item.date) if hasattr(item, 'date') else ''
                            }
                            df_data.append(record)

                        if df_data:
                            df = pd.DataFrame(df_data)
                            df_sorted = self.time_formatter.sort_by_time(df)

                            # 保持原始对象类型，只重新排序
                            data = [data[i] for i in range(len(data)) if i < len(df_sorted)]
                    except Exception as e:
                        print(f"[WARN] 时间排序失败，使用原始顺序: {e}")

                # 2. 数据去重
                if enable_deduplication:
                    try:
                        # 转换为DataFrame进行去重
                        df_data = []
                        for item in data:
                            record = {
                                'time': str(item.time) if hasattr(item, 'time') else '',
                                'price': float(item.price) if hasattr(item, 'price') else 0,
                                'volume': int(item.volume) if hasattr(item, 'volume') else 0,
                                'amount': float(getattr(item, 'amount', 0)),
                                'direction': str(getattr(item, 'direction', 'N')),
                                'code': str(getattr(item, 'code', '')),
                                'date': str(item.date) if hasattr(item, 'date') else ''
                            }
                            df_data.append(record)

                        if df_data:
                            df = pd.DataFrame(df_data)
                            # 对分笔数据按时间、价格、成交量进行去重
                            df_dedup = self.data_deduplicator.remove_duplicates(
                                df, key_columns=['time', 'price', 'volume']
                            )

                            # 转换回对象列表（保持原始对象顺序）
                            dedup_indices = df_dedup.index.tolist()
                            data = [data[i] for i in dedup_indices if i < len(data)]
                    except Exception as e:
                        print(f"[WARN] 数据去重失败，使用原始数据: {e}")

                self.stats['duplicates_removed'] = original_count - len(data) if enable_deduplication else 0

                self.stats['unique_records'] = len(data)

            self.stats['end_time'] = datetime.now()
            self.stats['total_records'] = len(data)
            self.stats['success'] = len(data) > 0

            return data

        except Exception as e:
            self.stats['error_message'] = str(e)
            self.stats['end_time'] = datetime.now()
            return []

    def get_stats(self) -> dict:
        """获取执行统计"""
        stats = self.stats.copy()
        if stats['start_time'] and stats['end_time']:
            stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
        return stats

    def generate_enhanced_report(self, data: List) -> dict:
        """
        生成增强数据质量报告

        Args:
            data: 分笔数据列表

        Returns:
            dict: 增强报告包含统计分析
        """
        if not data:
            return {
                'basic_quality': {'completeness_score': 0, 'time_coverage': 0.0, 'quality_grade': 'E'},
                'statistical_analysis': {},
                'data_characteristics': {},
                'processing_stats': self.get_stats()
            }

        # 基础质量报告
        basic_quality = generate_quality_report(data)

        # 统计分析
        statistical_analysis = {}
        try:
            # 转换为DataFrame进行统计
            df_data = []
            for item in data:
                record = {
                    'price': float(item.price) if hasattr(item, 'price') else 0,
                    'volume': int(item.volume) if hasattr(item, 'volume') else 0,
                    'amount': float(getattr(item, 'amount', 0))
                }
                df_data.append(record)

            if df_data:
                df = pd.DataFrame(df_data)
                summary_report = self.statistics_generator.generate_summary_report(df)
                statistical_analysis = summary_report.get('columns', {})

        except Exception as e:
            print(f"[WARN] 统计分析失败: {e}")

        # 数据特征分析
        data_characteristics = {}
        try:
            if data:
                # 价格特征
                prices = [float(item.price) for item in data if hasattr(item, 'price')]
                if prices:
                    data_characteristics['price_stats'] = self.statistics_generator.basic_stats(prices)

                # 成交量特征
                volumes = [int(item.volume) for item in data if hasattr(item, 'volume')]
                if volumes:
                    data_characteristics['volume_stats'] = self.statistics_generator.basic_stats(volumes)

                # 时间分布
                times = [str(item.time) for item in data if hasattr(item, 'time')]
                if times:
                    data_characteristics['time_span'] = {
                        'start_time': min(times),
                        'end_time': max(times),
                        'total_records': len(times)
                    }

        except Exception as e:
            print(f"[WARN] 数据特征分析失败: {e}")

        return {
            'basic_quality': basic_quality,
            'statistical_analysis': statistical_analysis,
            'data_characteristics': data_characteristics,
            'processing_stats': self.get_stats()
        }

    async def close(self):
        """关闭引擎"""
        if hasattr(self.data_source, 'close'):
            await self.data_source.close()



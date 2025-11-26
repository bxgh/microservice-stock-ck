#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件导出工具
统一的CSV和Excel导出功能
优化性能，支持大数据集快速导出
"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Any
import warnings

# 忽略openpyxl的警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


def export_to_csv(data: List[Any], filename: str, sort_by_time: bool = True) -> bool:
    """
    导出数据到CSV文件

    Args:
        data: 数据列表
        filename: 文件名
        sort_by_time: 是否按时间排序

    Returns:
        bool: 导出是否成功
    """
    if not data:
        print("[WARN] 没有数据可导出")
        return False

    try:
        # 转换为DataFrame
        df = _convert_to_dataframe(data)

        # 按时间排序
        if sort_by_time and 'time' in df.columns:
            df = _sort_dataframe_by_time(df)

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # 导出CSV
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        file_size = os.path.getsize(filename)
        print(f"[OK] CSV文件已保存: {filename} ({file_size/1024:.1f} KB)")
        return True

    except Exception as e:
        print(f"[ERROR] CSV导出失败: {e}")
        return False


def export_to_excel(data: List[Any], filename: str, sort_by_time: bool = True,
                    chunk_size: int = 50000) -> bool:
    """
    导出数据到Excel文件

    Args:
        data: 数据列表
        filename: 文件名
        sort_by_time: 是否按时间排序
        chunk_size: 分块大小，大数据集时使用分批处理

    Returns:
        bool: 导出是否成功
    """
    if not data:
        print("[WARN] 没有数据可导出")
        return False

    try:
        # 转换为DataFrame
        df = _convert_to_dataframe(data)

        # 按时间排序
        if sort_by_time and 'time' in df.columns:
            df = _sort_dataframe_by_time(df)

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # 性能优化策略：根据数据大小选择不同的写入方式
        data_size = len(df)

        if data_size <= 10000:
            # 小数据集：直接写入
            df.to_excel(filename, index=False, engine='openpyxl')
        elif data_size <= 50000:
            # 中等数据集：优化写入
            try:
                writer = pd.ExcelWriter(filename, engine='openpyxl')
                df.to_excel(writer, index=False)
                writer.close()
            except:
                # 回退到默认引擎
                df.to_excel(filename, index=False)
        else:
            # 大数据集：分批写入 + 内存优化
            try:
                writer = pd.ExcelWriter(filename, engine='xlsxwriter')
                # 先写入列头
                header_df = pd.DataFrame(columns=df.columns)
                header_df.to_excel(writer, index=False, startrow=0)

                # 分批写入数据
                chunks = [df[i:i + chunk_size] for i in range(0, data_size, chunk_size)]

                for i, chunk in enumerate(chunks):
                    start_row = i * chunk_size + 1  # +1 跳过标题行
                    chunk.to_excel(writer, index=False, startrow=start_row, header=False)

                    # 强制垃圾回收释放内存
                    del chunk

                writer.close()
            except ImportError:
                # xlsxwriter不可用，回退到默认方法
                df.to_excel(filename, index=False)
            except Exception:
                # 其他错误，回退到默认方法
                df.to_excel(filename, index=False)

        file_size = os.path.getsize(filename)
        print(f"[OK] Excel文件已保存: {filename} ({file_size/1024:.1f} KB)")
        return True

    except ImportError:
        # 回退到默认方法
        try:
            df.to_excel(filename, index=False)
            file_size = os.path.getsize(filename)
            print(f"[OK] Excel文件已保存: {filename} ({file_size/1024:.1f} KB) [fallback]")
            return True
        except Exception as fallback_e:
            print(f"[ERROR] Excel导出失败: {fallback_e}")
            return False
    except Exception as e:
        print(f"[ERROR] Excel导出失败: {e}")
        return False


def _convert_to_dataframe(data: List[Any]) -> pd.DataFrame:
    """
    将数据列表转换为DataFrame

    Args:
        data: 数据列表

    Returns:
        pd.DataFrame: 转换后的DataFrame
    """
    if not data:
        return pd.DataFrame()

    # 处理TickData对象
    if hasattr(data[0], 'time') and hasattr(data[0], 'price'):
        records = []
        for item in data:
            record = {
                'time': item.time.strftime('%H:%M:%S') if hasattr(item.time, 'strftime') else str(item.time),
                'price': float(item.price),
                'volume': int(item.volume),
                'amount': float(getattr(item, 'amount', 0)),
                'direction': str(getattr(item, 'direction', 'N')),
                'code': str(getattr(item, 'code', '')),
                'date': item.date.strftime('%Y-%m-%d') if hasattr(item.date, 'strftime') else str(item.date)
            }
            records.append(record)
        return pd.DataFrame(records)

    # 处理字典数据
    elif isinstance(data[0], dict):
        return pd.DataFrame(data)

    # 处理其他类型
    else:
        return pd.DataFrame(data)


def _sort_dataframe_by_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    按时间排序DataFrame - 高效实现

    Args:
        df: 原始DataFrame

    Returns:
        pd.DataFrame: 排序后的DataFrame
    """
    if df.empty or 'time' not in df.columns:
        return df

    try:
        # 高效时间排序：避免不必要的复制
        # 创建时间解析函数，支持多种格式
        def parse_time_string(time_str):
            try:
                # 尝试HH:MM:SS格式
                if ':' in str(time_str):
                    parts = str(time_str).split(':')
                    if len(parts) == 3:
                        h, m, s = parts
                        return int(h) * 3600 + int(m) * 60 + int(s)
                    elif len(parts) == 2:
                        h, m = parts
                        return int(h) * 3600 + int(m) * 60
                return 0
            except:
                return 0

        # 使用向量化操作解析时间
        time_series = df['time'].astype(str)

        # 尝试pandas的to_datetime（对于标准格式更快）
        try:
            time_seconds = pd.to_datetime(time_series, format='%H:%M:%S', errors='coerce')
            valid_mask = time_seconds.notna()

            if valid_mask.all():
                # 全部标准格式，直接排序
                df_sorted = df.loc[time_seconds.argsort()].reset_index(drop=True)
                return df_sorted
            else:
                # 混合格式，需要额外处理
                time_seconds = time_seconds.fillna(
                    pd.to_datetime(time_series[~valid_mask], format='%H:%M', errors='coerce')
                )
                # 最终排序
                sort_indices = time_seconds.argsort()
                df_sorted = df.iloc[sort_indices].reset_index(drop=True)
                return df_sorted

        except:
            # 回退到自定义解析
            time_seconds = time_series.apply(parse_time_string)
            sort_indices = time_seconds.argsort()
            df_sorted = df.iloc[sort_indices].reset_index(drop=True)
            return df_sorted

    except Exception as e:
        print(f"[WARN] 时间排序失败，使用原始顺序: {e}")
        return df
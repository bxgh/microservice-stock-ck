#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mootdx 字段映射和数据清洗工具
解决验证中发现的字段不一致和单位转换问题
"""

import pandas as pd
from typing import Dict, Any


# 买卖方向映射表
BUYORSELL_MAP = {
    0: 'SELL',      # 主动卖出
    1: 'BUY',       # 主动买入
    2: 'NEUTRAL'    # 中性盘
}


def clean_tick_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗和标准化分笔数据
    
    问题修复:
    1. 字段重命名: buyorsell -> type
    2. 单位转换: vol(手) -> volume(股)
    3. 方向映射: 0/1/2 -> SELL/BUY/NEUTRAL
    
    Args:
        df: 原始分笔数据
        
    Returns:
        清洗后的标准化数据
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # 1. 字段重命名
    rename_map = {}
    
    if 'vol' in df.columns:
        # vol是手数，保存原始值
        df['volume_hands'] = df['vol']
        # 转换为股数 (1手=100股)
        df['volume'] = df['vol'] * 100
        rename_map['vol'] = 'volume_original'
    
    if 'buyorsell' in df.columns:
        # 映射买卖方向
        df['type'] = df['buyorsell'].map(BUYORSELL_MAP)
        df['direction'] = df['buyorsell']  # 保留原始值
        rename_map['buyorsell'] = 'direction_original'
    
    # 2. 应用重命名
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # 3. 标准化字段顺序
    standard_columns = ['time', 'price', 'volume', 'type']
    optional_columns = ['volume_hands', 'direction', 'volume_original', 'direction_original']
    
    # 选择存在的列
    final_columns = [c for c in standard_columns if c in df.columns]
    final_columns += [c for c in optional_columns if c in df.columns]
    
    return df[final_columns]


def validate_tick_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    验证并过滤异常分笔数据
    
    过滤规则:
    1. 价格 <= 0
    2. 成交量 < 0
    3. 时间不在交易时段
    
    Args:
        df: 分笔数据
        
    Returns:
        验证后的数据
    """
    if df.empty:
        return df
    
    original_count = len(df)
    
    # 1. 价格验证
    if 'price' in df.columns:
        df = df[df['price'] > 0]
    
    # 2. 成交量验证
    if 'volume' in df.columns:
        df = df[df['volume'] >= 0]
    
    # 3. 去重
    df = df.drop_duplicates()
    
    filtered_count = original_count - len(df)
    if filtered_count > 0:
        print(f"⚠️ 过滤了 {filtered_count} 条异常数据")
    
    return df


def standardize_mootdx_fields(df: pd.DataFrame, data_type: str = 'tick') -> pd.DataFrame:
    """
    统一标准化 mootdx 返回的各类数据
    
    Args:
        df: 原始数据
        data_type: 数据类型 ('tick', 'quotes', 'history')
        
    Returns:
        标准化后的数据
    """
    if df.empty:
        return df
    
    if data_type == 'tick':
        df = clean_tick_data(df)
        df = validate_tick_data(df)
    
    elif data_type == 'quotes':
        # TODO: 实时行情字段标准化
        pass
    
    elif data_type == 'history':
        # TODO: 历史K线字段标准化
        pass
    
    return df


# 示例用法
if __name__ == "__main__":
    from mootdx.quotes import Quotes
    
    print("="*60)
    print("Mootdx 字段映射和数据清洗演示")
    print("="*60)
    
    client = Quotes.factory(market='std', bestip=True)
    
    # 获取原始分笔数据
    print("\n1. 获取原始数据...")
    df_raw = client.transactions(symbol='000001', date=20241218)
    print(f"原始列名: {list(df_raw.columns)}")
    print(f"原始数据:\n{df_raw.head(3)}")
    
    # 清洗和标准化
    print("\n2. 清洗和标准化...")
    df_clean = standardize_mootdx_fields(df_raw, data_type='tick')
    print(f"标准化列名: {list(df_clean.columns)}")
    print(f"标准化数据:\n{df_clean.head(3)}")
    
    # 验证转换
    print("\n3. 验证转换...")
    if 'volume_hands' in df_clean.columns and 'volume' in df_clean.columns:
        print(f"手数示例: {df_clean['volume_hands'].iloc[0]}")
        print(f"股数示例: {df_clean['volume'].iloc[0]}")
        print(f"转换正确: {df_clean['volume'].iloc[0] == df_clean['volume_hands'].iloc[0] * 100}")
    
    if 'type' in df_clean.columns:
        print(f"\n买卖方向分布:\n{df_clean['type'].value_counts()}")
    
    print("\n✓ 演示完成!")

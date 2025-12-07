# -*- coding: utf-8 -*-
"""
EPIC-007 分笔成交数据分析器

提供分笔数据的通用分析功能:
1. 买卖方向判断
2. 大单识别
3. 资金流向计算
4. 分时段分析

@author: EPIC-007 Story 007.02b
@date: 2025-12-07
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np

from .schemas import CapitalFlowResult

logger = logging.getLogger(__name__)


# 大单分级标准 (元)
LARGE_ORDER_THRESHOLDS = {
    'super_large': 1_000_000,  # 100万 - 超大单
    'large': 500_000,          # 50万 - 大单
    'medium': 200_000,         # 20万 - 中单
    'small': 0,                # 散单
}

# 交易时段划分
TIME_PERIODS = {
    'morning_open': ('09:30:00', '10:00:00'),   # 早盘集合竞价后
    'morning': ('10:00:00', '11:30:00'),        # 上午交易
    'afternoon_open': ('13:00:00', '14:00:00'), # 下午开盘
    'afternoon': ('14:00:00', '15:00:00'),      # 尾盘
}


class TickAnalyzer:
    """分笔成交数据分析器
    
    提供通用的分笔数据分析方法，避免每个策略重复实现。
    所有方法都是静态方法，可以直接调用。
    
    Example:
        # 判断买卖方向
        df_with_direction = TickAnalyzer.calculate_direction(df)
        
        # 识别大单
        large_orders = TickAnalyzer.identify_large_orders(df, threshold=500_000)
        
        # 计算资金流向
        flow = TickAnalyzer.calculate_capital_flow(df, code='000001', date='2025-12-07')
    """
    
    @staticmethod
    def calculate_direction(df: pd.DataFrame) -> pd.DataFrame:
        """计算买卖方向
        
        算法:
        1. 如果成交价 > 上一笔成交价 -> 主动买入 (B)
        2. 如果成交价 < 上一笔成交价 -> 主动卖出 (S)
        3. 如果成交价 = 上一笔成交价:
           - 使用 tick_type 辅助判断 (0=买盘, 1=卖盘)
           - 如果无 tick_type -> 中性 (N)
        
        Args:
            df: 分笔数据 DataFrame (必须有 price 列，按时间排序)
            
        Returns:
            pd.DataFrame: 添加 direction 列的 DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 计算价格变化
        df['price_change'] = df['price'].diff()
        
        # 根据价格变化判断方向
        conditions = [
            df['price_change'] > 0,  # 价格上涨
            df['price_change'] < 0,  # 价格下跌
        ]
        choices = ['B', 'S']
        
        # 默认中性
        df['direction'] = 'N'
        
        # 应用条件
        df['direction'] = np.select(conditions, choices, default='N')
        
        # 处理平盘情况 (price_change == 0 或 NaN)
        if 'tick_type' in df.columns:
            # 使用 tick_type 辅助判断平盘
            flat_mask = (df['price_change'] == 0) | df['price_change'].isna()
            df.loc[flat_mask & (df['tick_type'] == 0), 'direction'] = 'B'
            df.loc[flat_mask & (df['tick_type'] == 1), 'direction'] = 'S'
        
        # 第一笔默认为中性
        df.loc[0, 'direction'] = 'N'
        
        # 移除辅助列
        df.drop(columns=['price_change'], inplace=True)
        
        return df
    
    @staticmethod
    def identify_large_orders(
        df: pd.DataFrame,
        threshold: float = 500_000,
        direction: Optional[str] = None,
    ) -> pd.DataFrame:
        """识别大单
        
        Args:
            df: 分笔数据 DataFrame (必须有 amount 和 direction 列)
            threshold: 金额阈值 (元)，默认50万
            direction: 方向过滤 ('B'/'S'/None)，None表示不过滤
            
        Returns:
            pd.DataFrame: 大单列表
        """
        if df.empty:
            return df
        
        # 筛选大单
        large_orders = df[df['amount'] >= threshold].copy()
        
        # 方向过滤
        if direction:
            large_orders = large_orders[large_orders['direction'] == direction]
        
        # 添加订单等级
        large_orders['order_level'] = large_orders['amount'].apply(
            TickAnalyzer._classify_order_size
        )
        
        return large_orders
    
    @staticmethod
    def _classify_order_size(amount: float) -> str:
        """分类订单大小"""
        if amount >= LARGE_ORDER_THRESHOLDS['super_large']:
            return '超大单'
        elif amount >= LARGE_ORDER_THRESHOLDS['large']:
            return '大单'
        elif amount >= LARGE_ORDER_THRESHOLDS['medium']:
            return '中单'
        else:
            return '小单'
    
    @staticmethod
    def calculate_capital_flow(
        df: pd.DataFrame,
        code: str,
        date: str,
        large_threshold: float = 500_000,
    ) -> CapitalFlowResult:
        """计算资金流向
        
        Args:
            df: 分笔数据 DataFrame (必须有 direction 和 amount 列)
            code: 股票代码
            date: 交易日期
            large_threshold: 大单阈值
            
        Returns:
            CapitalFlowResult: 资金流向分析结果
        """
        if df.empty:
            return CapitalFlowResult(
                code=code,
                date=date,
                total_buy_amount=0,
                total_sell_amount=0,
                net_inflow=0,
                large_order_count=0,
                large_order_amount=0,
                buy_sell_ratio=0,
            )
        
        # 确保有 direction 列
        if 'direction' not in df.columns:
            df = TickAnalyzer.calculate_direction(df)
        
        # 计算买卖金额
        buy_mask = df['direction'] == 'B'
        sell_mask = df['direction'] == 'S'
        
        total_buy_amount = df.loc[buy_mask, 'amount'].sum()
        total_sell_amount = df.loc[sell_mask, 'amount'].sum()
        net_inflow = total_buy_amount - total_sell_amount
        
        # 计算买卖比
        buy_sell_ratio = (
            total_buy_amount / total_sell_amount 
            if total_sell_amount > 0 else 0
        )
        
        # 识别大单
        large_orders = TickAnalyzer.identify_large_orders(df, threshold=large_threshold)
        large_order_count = len(large_orders)
        large_order_amount = large_orders['amount'].sum()
        
        # 分时段分析
        time_analysis = TickAnalyzer.analyze_by_time_period(df)
        
        return CapitalFlowResult(
            code=code,
            date=date,
            total_buy_amount=total_buy_amount,
            total_sell_amount=total_sell_amount,
            net_inflow=net_inflow,
            large_order_count=large_order_count,
            large_order_amount=large_order_amount,
            buy_sell_ratio=buy_sell_ratio,
            time_analysis=time_analysis,
        )
    
    @staticmethod
    def analyze_by_time_period(df: pd.DataFrame) -> Dict[str, Dict]:
        """分时段资金分析
        
        Args:
            df: 分笔数据 DataFrame (必须有 time, direction, amount 列)
            
        Returns:
            Dict: 各时段的资金统计
            {
                'morning_open': {'buy': xxx, 'sell': xxx, 'net': xxx},
                'morning': {...},
                'afternoon_open': {...},
                'afternoon': {...},
            }
        """
        if df.empty or 'time' not in df.columns:
            return {}
        
        # 确保有 direction 列
        if 'direction' not in df.columns:
            df = TickAnalyzer.calculate_direction(df)
        
        result = {}
        
        for period_name, (start_time, end_time) in TIME_PERIODS.items():
            # 筛选时段数据
            period_mask = (df['time'] >= start_time) & (df['time'] < end_time)
            period_df = df[period_mask]
            
            if period_df.empty:
                result[period_name] = {
                    'buy_amount': 0,
                    'sell_amount': 0,
                    'net_inflow': 0,
                    'tick_count': 0,
                }
                continue
            
            # 计算该时段的买卖金额
            buy_amount = period_df[period_df['direction'] == 'B']['amount'].sum()
            sell_amount = period_df[period_df['direction'] == 'S']['amount'].sum()
            net_inflow = buy_amount - sell_amount
            
            result[period_name] = {
                'buy_amount': float(buy_amount),
                'sell_amount': float(sell_amount),
                'net_inflow': float(net_inflow),
                'tick_count': len(period_df),
            }
        
        return result
    
    @staticmethod
    def get_tick_summary(df: pd.DataFrame) -> Dict:
        """获取分笔统计摘要
        
        Args:
            df: 分笔数据 DataFrame
            
        Returns:
            Dict: 统计摘要
        """
        if df.empty:
            return {
                'total_volume': 0,
                'total_amount': 0,
                'tick_count': 0,
                'avg_price': 0,
                'price_range': [0, 0],
            }
        
        return {
            'total_volume': int(df['volume'].sum()),
            'total_amount': float(df['amount'].sum()),
            'tick_count': len(df),
            'avg_price': float(df['price'].mean()),
            'price_range': [float(df['price'].min()), float(df['price'].max())],
        }

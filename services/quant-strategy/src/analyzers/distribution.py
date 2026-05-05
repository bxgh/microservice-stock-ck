"""
DistributionAnalyzer - 分布分析器
计算目标股票特征在同类股分布中的分位点 (Percentile)
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .interfaces import IAnalyzer

class DistributionAnalyzer:
    """
    分位数分析器
    用于衡量目标股票在同行业/同类股中的相对位置
    """
    
    def analyze(
        self, 
        target_df: pd.DataFrame, 
        peers_df: pd.DataFrame, 
        features: List[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        分析分位点
        
        Args:
            target_df: 目标股特征矩阵 (需包含 trade_date)
            peers_df: 同类股特征矩阵
            features: 待分析的特征列表 (默认为 f1-f9)
            
        Returns:
            Dict: {date: {feature: percentile}}
        """
        if target_df.empty or peers_df.empty:
            return {}
            
        if features is None:
            features = [f'f{i}' for i in range(1, 10)]
            
        results = {}
        
        # 按日期循环分析 (通常取最新日期或指定日期范围)
        common_dates = sorted(target_df['trade_date'].unique(), reverse=True)
        
        for date in common_dates:
            target_row = target_df[target_df['trade_date'] == date]
            if target_row.empty:
                continue
                
            peer_pool = peers_df[peers_df['trade_date'] == date]
            if peer_pool.empty:
                continue
                
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            results[date_str] = {}
            
            for feat in features:
                if feat not in target_row.columns or feat not in peer_pool.columns:
                    continue
                
                target_val = target_row[feat].iloc[0]
                peer_vals = peer_pool[feat].values
                
                # 计算分位点 (Percentile Rank)
                # (小于等于 target_val 的数量) / 总数
                percentile = (peer_vals <= target_val).mean() * 100
                results[date_str][feat] = round(float(percentile), 2)
                
        return results

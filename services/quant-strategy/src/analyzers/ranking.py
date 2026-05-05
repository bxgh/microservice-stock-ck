"""
RankingAnalyzer - 排名分析器
对目标股票与同类股进行多维度排序，识别强势/弱势特征
"""
import pandas as pd
from typing import Dict, Any, List
from .interfaces import IAnalyzer

class RankingAnalyzer:
    """
    排名分析器
    识别目标股票在同类群组中的排名
    """
    
    def analyze(
        self, 
        target_df: pd.DataFrame, 
        peers_df: pd.DataFrame, 
        features: List[str] = None,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        分析排名
        
        Returns:
            Dict: {date: {'rankings': {feature: rank}, 'top_peers': {feature: List}}}
        """
        if target_df.empty or peers_df.empty:
            return {}
            
        if features is None:
            features = [f'f{i}' for i in range(1, 10)]
            
        results = {}
        
        # 只取最新一天进行详细排名分析
        latest_date = target_df['trade_date'].max()
        if pd.isna(latest_date):
            return {}
            
        target_row = target_df[target_df['trade_date'] == latest_date]
        peer_pool = peers_df[peers_df['trade_date'] == latest_date]
        
        if target_row.empty or peer_pool.empty:
            return {}
            
        date_str = latest_date.strftime('%Y-%m-%d') if hasattr(latest_date, 'strftime') else str(latest_date)
        results[date_str] = {
            'rankings': {},
            'top_peers': {}
        }
        
        # 合并目标和对手进行统一排序
        combined = pd.concat([target_row, peer_pool], ignore_index=True)
        
        for feat in features:
            if feat not in combined.columns:
                continue
                
            # 降序排序 (数值越大排名越前)
            combined_sorted = combined.sort_values(by=feat, ascending=False).reset_index()
            
            # 找到目标的排名
            target_rank_idx = combined_sorted[combined_sorted['ts_code'] == target_row['ts_code'].iloc[0]].index
            if len(target_rank_idx) > 0:
                rank = target_rank_idx[0] + 1
                total = len(combined_sorted)
                results[date_str]['rankings'][feat] = f"{rank}/{total}"
            
            # 记录该维度前 N 名
            results[date_str]['top_peers'][feat] = combined_sorted.head(top_n)[['ts_code', feat]].to_dict(orient='records')
            
        return results

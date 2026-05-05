import pandas as pd
from typing import Optional
from .models import RecoveryMetrics
from .interfaces import IAnalyzer

class RecoveryAnalyzer(IAnalyzer):
    """复苏统计分析器"""
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> RecoveryMetrics:
        """
        分析股价复苏情况
        
        Args:
            df: K 线数据
            kwargs: 必须包含 'peak_price' (float) 和 'trough_date' (str/date)
        """
        peak_price = kwargs.get('peak_price')
        trough_date = kwargs.get('trough_date')
        
        if df.empty or peak_price is None or trough_date is None:
            return RecoveryMetrics(is_recovered=False)
            
        # 转换为字符串日期对比 (或 pd.Timestamp)
        trough_ts = pd.to_datetime(trough_date)
        
        # 1. 查找谷底之后的 K 线
        df_post_trough = df[pd.to_datetime(df['date']) > trough_ts]
        
        if df_post_trough.empty:
            return RecoveryMetrics(is_recovered=False)
            
        # 2. 检查是否收复高点
        recovery_df = df_post_trough[df_post_trough['close'] >= peak_price]
        
        if not recovery_df.empty:
            recovery_date = recovery_df.iloc[0]['date']
            recovery_date_ts = pd.to_datetime(recovery_date)
            # 计算天数 (通过原始索引差异)
            recovery_idx = recovery_df.index[0]
            trough_idx = df[pd.to_datetime(df['date']) == trough_ts].index[0]
            recovery_days = int(recovery_idx - trough_idx)
            
            return RecoveryMetrics(
                is_recovered=True,
                recovery_days=recovery_days
            )
            
        return RecoveryMetrics(is_recovered=False)

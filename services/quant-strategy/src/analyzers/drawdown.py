import numpy as np
import pandas as pd
from .models import DrawdownMetrics
from .interfaces import IAnalyzer

class DrawdownAnalyzer(IAnalyzer):
    """回撤分析器"""
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> DrawdownMetrics:
        """
        识别首波峰谷并计算回撤相关指标
        
        预期数据: 包含上市首日至今的全周期 K 线
        """
        if df.empty:
            return DrawdownMetrics(0.0, "", 0.0, "", 0.0, 0, 0)
            
        # 1. 识别首波峰值 (上市后 120 个交易日内)
        # 根据实施计划: max(high[:120])
        window_peak = 120
        df_peak_search = df.iloc[:window_peak]
        peak_idx = df_peak_search['high'].idxmax()
        peak_price = df_peak_search.loc[peak_idx, 'high']
        # 格式化日期，只保留 YYYY-MM-DD
        peak_date = pd.to_datetime(df_peak_search.loc[peak_idx, 'date']).strftime('%Y-%m-%d')
        
        # 2. 识别首波谷底 (从峰值当天开始搜寻，或者峰值后一天？通常含峰值当天以防当天跳水)
        window_trough = 180
        peak_pos = df.index.get_loc(peak_idx)
        df_trough_search = df.iloc[peak_pos : peak_pos + window_trough]
        
        if df_trough_search.empty:
            df_trough_search = df.iloc[peak_pos:]
            
        trough_idx = df_trough_search['low'].idxmin()
        trough_price = df_trough_search.loc[trough_idx, 'low']
        trough_date = pd.to_datetime(df_trough_search.loc[trough_idx, 'date']).strftime('%Y-%m-%d')
        
        # 3. 计算指标
        drawdown_pct = (trough_price - peak_price) / peak_price
        
        # 使用位置索引计算天数 (相对时间)
        trough_pos = df.index.get_loc(trough_idx)
        peak_days = peak_pos  # 距上市首日的天数
        trough_days = trough_pos - peak_pos  # 从峰值到谷底的天数
        
        return DrawdownMetrics(
            first_peak_price=float(peak_price),
            first_peak_date=peak_date,
            first_trough_price=float(trough_price),
            first_trough_date=trough_date,
            drawdown_pct=float(drawdown_pct),
            peak_days=int(peak_days),
            trough_days=int(trough_days)
        )

import numpy as np
import pandas as pd
from .models import VolatilityMetrics
from .interfaces import IAnalyzer

class VolatilityAnalyzer(IAnalyzer):
    """波动率分析器"""
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> VolatilityMetrics:
        if df.empty:
            return VolatilityMetrics(0.0, 0.0, 0.0)
            
        # 1. 计算年化波动率 (需要至少2行)
        annual_vol = 0.0
        if len(df) >= 2:
            log_returns = np.log(df['close'] / df['close'].shift(1)).dropna()
            if len(log_returns) > 0:
                annual_vol = log_returns.std() * np.sqrt(252)
            
        # 2. 计算振幅 (单行即可计算)
        amplitudes = (df['high'] - df['low']) / df['low']
        avg_amp = amplitudes.mean()
        max_amp = amplitudes.max()
        
        return VolatilityMetrics(
            annual_volatility=float(annual_vol),
            avg_amplitude=float(avg_amp),
            max_amplitude=float(max_amp)
        )

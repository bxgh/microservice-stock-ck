import pandas as pd
from .models import LiquidityMetrics
from .interfaces import IAnalyzer

class LiquidityProfiler(IAnalyzer):
    """流动性画像分析器"""
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> LiquidityMetrics:
        """
        分析流动性指标
        
        Args:
            df: 必须包含 'turnover' 列
        """
        if df.empty or 'turnover' not in df.columns:
            return LiquidityMetrics(0.0, 0.0, 1.0, 0)
            
        # 1. 平均换手率 (全周期)
        avg_turnover = df['turnover'].mean()
        
        # 2. 近期换手率 (最近 5 日)
        recent_window = 5
        recent_turnover = df['turnover'].iloc[-recent_window:].mean()
        
        # 3. 换手衰减率 (近期 / 均值)
        # 如果均值为 0，衰减率为 1.0 (防止除以零)
        decay_rate = 1.0
        if avg_turnover > 0:
            decay_rate = recent_turnover / avg_turnover
            
        # 4. 高活跃天数 (换手率 > 10%)
        # 次新股早期换手率通常很高，所以此指标衡量人气持续度
        hot_days = (df['turnover'] > 10.0).sum()
        
        return LiquidityMetrics(
            avg_turnover=float(avg_turnover),
            recent_turnover=float(recent_turnover),
            decay_rate=float(decay_rate),
            hot_days=int(hot_days)
        )

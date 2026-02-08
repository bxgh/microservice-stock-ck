import numpy as np
import pandas as pd
from .models import BetaMetrics
from .interfaces import IAnalyzer

class BetaCalculator(IAnalyzer):
    """Beta 系数计算器"""
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> BetaMetrics:
        """
        计算 Beta 系数
        
        Args:
            df: 个股 K 线
            kwargs: 必须包含 'benchmark_df' (指数 K 线)
        """
        benchmark_df = kwargs.get('benchmark_df')
        
        if df.empty or benchmark_df is None or benchmark_df.empty:
            return BetaMetrics(1.0, "跟随型")
            
        # 对齐日期
        # 假设 df 和 benchmark_df 都有 'date' 列并已排序
        df = df.set_index('date')
        benchmark_df = benchmark_df.set_index('date')
        
        # 计算日收益率
        stock_returns = df['close'].pct_change().dropna()
        bench_returns = benchmark_df['close'].pct_change().dropna()
        
        # 取交集
        common_idx = stock_returns.index.intersection(bench_returns.index)
        if len(common_idx) < 10: # 样本太少不具参考意义
            return BetaMetrics(1.0, "跟随型")
            
        s_ret = stock_returns.loc[common_idx]
        b_ret = bench_returns.loc[common_idx]
        
        # 计算 Beta = Cov(rs, rb) / Var(rb)
        covariance = np.cov(s_ret, b_ret)[0, 1]
        variance = np.var(b_ret)
        
        if variance == 0:
            beta = 1.0
        else:
            beta = covariance / variance
            
        # 分类逻辑: >1.2 进攻型, <0.8 独立型, 其他跟随型
        if beta > 1.2:
            category = "进攻型"
        elif beta < 0.8:
            category = "独立型"
        else:
            category = "跟随型"
            
        return BetaMetrics(beta=float(beta), category=category)

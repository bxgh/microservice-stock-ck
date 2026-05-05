import pytest
import pandas as pd
import numpy as np
from analyzers.liquidity import LiquidityProfiler
from analyzers.recovery import RecoveryAnalyzer

def test_liquidity_profiler():
    """测试流动性画像"""
    df = pd.DataFrame({
        'turnover': [5.0, 12.0, 8.0, 4.0, 6.0, 15.0, 3.0, 2.0, 1.0, 4.0]
    })
    
    analyzer = LiquidityProfiler()
    metrics = analyzer.analyze(df)
    
    # Avg: sum(60)/10 = 6.0
    assert metrics.avg_turnover == 6.0
    # Recent (5): (15+3+2+1+4)/5 = 5.0
    assert metrics.recent_turnover == 5.0
    # Decay: 5/6 = 0.8333
    assert metrics.decay_rate == pytest.approx(5.0/6.0)
    # Hot days (>10): 12.0 and 15.0 -> 2 days
    assert metrics.hot_days == 2

def test_recovery_analyzer():
    """测试复苏分析"""
    dates = pd.date_range(start='2026-01-01', periods=15)
    # Peak at Day 0: 200
    # Trough at Day 5: 50
    # Recovered at Day 12: 210
    prices = [200, 150, 100, 80, 60, 50, 70, 90, 120, 160, 190, 210, 220, 200, 190]
    df = pd.DataFrame({'date': dates, 'close': prices})
    
    analyzer = RecoveryAnalyzer()
    # 模拟输入
    peak_price = 200.0
    trough_date = dates[5] # 2026-01-06
    
    metrics = analyzer.analyze(df, peak_price=peak_price, trough_date=trough_date)
    
    assert metrics.is_recovered == True
    # Day 5 to Day 11 (210) index diff?
    # trough_idx = 5, recovery_idx = 11. Days = 6
    assert metrics.recovery_days == 6

def test_recovery_analyzer_not_recovered():
    """测试未复苏情况"""
    dates = pd.date_range(start='2026-01-01', periods=10)
    prices = [200, 100, 50, 60, 70, 80, 90, 100, 110, 120]
    df = pd.DataFrame({'date': dates, 'close': prices})
    
    analyzer = RecoveryAnalyzer()
    metrics = analyzer.analyze(df, peak_price=200.0, trough_date=dates[2])
    
    assert metrics.is_recovered == False
    assert metrics.recovery_days is None

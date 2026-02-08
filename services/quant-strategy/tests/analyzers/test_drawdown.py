import pytest
import pandas as pd
import numpy as np
from analyzers.drawdown import DrawdownAnalyzer
from analyzers.models import DrawdownMetrics

def test_drawdown_analyzer_basic():
    """测试基本回撤分析"""
    # 构造假数据: 上市首日开始，先涨后跌
    # Day 0-10: 100 -> 200 (Peak at Day 10)
    # Day 11-20: 200 -> 50 (Trough at Day 20)
    dates = pd.date_range(start='2026-01-01', periods=30)
    highs = np.linspace(100, 200, 11).tolist() + np.linspace(190, 50, 10).tolist() + [60]*9
    lows = [h - 5 for h in highs]
    
    df = pd.DataFrame({
        'date': dates,
        'high': highs,
        'low': lows,
        'close': highs
    })
    
    analyzer = DrawdownAnalyzer()
    metrics = analyzer.analyze(df)
    
    assert isinstance(metrics, DrawdownMetrics)
    assert metrics.first_peak_price == 200.0
    assert metrics.first_peak_date == '2026-01-11' # Day 10
    assert metrics.first_trough_price == 45.0 # Day 20 low (50-5)
    assert metrics.drawdown_pct == pytest.approx((45-200)/200) # -0.775
    assert metrics.peak_days == 10
    assert metrics.trough_days == 10

def test_drawdown_analyzer_insufficient_data():
    """测试数据量不足 120 天的情况"""
    dates = pd.date_range(start='2026-01-01', periods=50)
    highs = [100]*25 + [300] + [200]*24
    lows = [h - 10 for h in highs]
    
    df = pd.DataFrame({
        'date': dates,
        'high': highs,
        'low': lows,
        'close': highs
    })
    
    analyzer = DrawdownAnalyzer()
    metrics = analyzer.analyze(df)
    
    assert metrics.first_peak_price == 300.0
    assert metrics.first_trough_price == 190.0 # 200-10
    assert metrics.peak_days == 25

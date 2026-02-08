import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from analyzers.multiples import MultiplesAnalyzer
from analyzers.beta import BetaCalculator

def test_multiples_analyzer():
    """测试倍数分析器"""
    dates = pd.date_range(start='2026-01-01', periods=10)
    df = pd.DataFrame({
        'date': dates,
        'open': [10.0] * 10,
        'high': [10, 15, 20, 18, 25, 22, 30, 28, 35, 32],
        'low': [9] * 10,
        'close': [10, 14, 19, 17, 24, 21, 29, 27, 34, 30]
    })
    
    issue_price = Decimal("10.0")
    analyzer = MultiplesAnalyzer()
    metrics = analyzer.analyze(df, issue_price=issue_price)
    
    # 1. 首波涨幅: (25 - 10) / 10 = 1.5
    # 注意: 前面 120 天，这里只有 10 天，所以全选。Peak 是 35. 
    # (35 - 10) / 10 = 2.5
    assert metrics.first_wave_gain == 2.5
    # 2. 最高/发行价: 35 / 10 = 3.5
    assert metrics.high_to_issue == 3.5
    # 3. 当前/发行价: 30 / 10 = 3.0
    assert metrics.current_to_issue == 3.0

def test_beta_calculator():
    """测试 Beta 计算器"""
    dates = pd.date_range(start='2026-01-01', periods=20)
    # 基准: 稳步增长
    bench_close = np.linspace(3000, 3300, 20)
    # 个股: 2倍杠杆基准
    stock_close = 100 * (bench_close / bench_close[0])**2
    
    df_stock = pd.DataFrame({'date': dates, 'close': stock_close})
    df_bench = pd.DataFrame({'date': dates, 'close': bench_close})
    
    calculator = BetaCalculator()
    metrics = calculator.analyze(df_stock, benchmark_df=df_bench)
    
    assert metrics.beta > 1.5 # 应该是接近 2
    assert metrics.category == "进攻型"

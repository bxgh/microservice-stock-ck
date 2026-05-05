import pytest
import pandas as pd
import numpy as np
from analyzers.volatility import VolatilityAnalyzer
from analyzers.models import VolatilityMetrics

def test_volatility_analyzer_basic():
    """测试基本波动率计算"""
    # 构造假数据: 5天数据
    data = {
        'date': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'],
        'open': [100, 105, 110, 108, 112],
        'high': [106, 112, 115, 110, 118],
        'low': [98, 104, 108, 105, 110],
        'close': [105, 110, 108, 112, 115]
    }
    df = pd.DataFrame(data)
    
    analyzer = VolatilityAnalyzer()
    metrics = analyzer.analyze(df)
    
    assert isinstance(metrics, VolatilityMetrics)
    assert metrics.annual_volatility > 0
    assert metrics.avg_amplitude > 0
    assert metrics.max_amplitude >= metrics.avg_amplitude
    
    # 验证 max_amplitude: (118-110)/110 = 8/110 = 0.0727...
    # (106-98)/98 = 8/98 = 0.0816... (Day 0)
    # (112-104)/104 = 8/104 = 0.0769... (Day 1)
    # (115-108)/108 = 7/108 = 0.0648... (Day 2)
    # (110-105)/105 = 5/105 = 0.0476... (Day 3)
    # Max should be Day 0: 0.0816...
    assert pytest.approx(metrics.max_amplitude, 0.001) == 0.0816326

def test_volatility_analyzer_empty():
    """测试空数据处理"""
    df = pd.DataFrame()
    analyzer = VolatilityAnalyzer()
    metrics = analyzer.analyze(df)
    assert metrics.annual_volatility == 0.0
    assert metrics.avg_amplitude == 0.0

def test_volatility_analyzer_single_row():
    """测试单行数据处理"""
    df = pd.DataFrame({'close': [100], 'high': [105], 'low': [95]})
    analyzer = VolatilityAnalyzer()
    metrics = analyzer.analyze(df)
    assert metrics.annual_volatility == 0.0
    # 即使单行，振幅也可以计算
    assert metrics.avg_amplitude == pytest.approx((105-95)/95)

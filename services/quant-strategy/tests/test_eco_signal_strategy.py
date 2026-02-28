import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.alt_data.eco_signal_strategy import EcoSignalStrategy

@pytest.fixture
def strategy():
    return EcoSignalStrategy()

def test_generate_signals_empty(strategy):
    res = strategy.generate_signals(pd.DataFrame())
    assert res.empty

def test_generate_signals_single_record(strategy):
    """测试在只有一条数据的情况下（极小样本），Z-score 容错并能输出合理的信号。"""
    raw_data = [{
        "collect_time": datetime.now(),
        "org": "test-org",
        "repo": "test-repo",
        "label": "test-label",
        "pr_merged_count": 10,
        "pr_merged_acceleration": 5,
        "issue_close_median_hours": 24,
        "star_delta_7d": 100,
        "commit_count_7d": 50,
        "contributor_count_30d": 10
    }]
    
    df = pd.DataFrame(raw_data)
    res = strategy.generate_signals(df)
    
    assert not res.empty
    assert res.iloc[0]['signal_level'] == "NEUTRAL"
    assert res.iloc[0]['composite_z_score'] == 0.0

def test_generate_signals_multiple_records(strategy):
    """测试多条记录，验证复合特征计算与Z-Score权重组合功能"""
    base_time = datetime(2026, 1, 1)
    
    # 模拟三天的数据
    # Day 1: 活跃度普通
    # Day 2: 活跃度下降
    # Day 3: 活跃度极高 (预期会有很大的 Z-score)
    
    raw_data = [
        {
            "collect_time": base_time,
            "org": "o1", "repo": "r1", "label": "deepseek",
            "pr_merged_acceleration": 10,
            "issue_close_median_hours": 48.0,
            "star_delta_7d": 50,
            "contributor_count_30d": 5
        },
        {
            "collect_time": base_time + timedelta(days=1),
            "org": "o1", "repo": "r1", "label": "deepseek",
            "pr_merged_acceleration": -5,
            "issue_close_median_hours": 72.0,
            "star_delta_7d": 10,
            "contributor_count_30d": 2
        },
        {
            "collect_time": base_time + timedelta(days=2),
            "org": "o1", "repo": "r1", "label": "deepseek",
            "pr_merged_acceleration": 50,
            "issue_close_median_hours": 2.0,
            "star_delta_7d": 500,
            "contributor_count_30d": 20
        }
    ]
    
    df = pd.DataFrame(raw_data)
    res = strategy.generate_signals(df, target_date=base_time + timedelta(days=2))
    
    assert not res.empty
    # 第三天的大幅暴涨应该让 Z-score 非常高
    assert res.iloc[0]['composite_z_score'] > 0
    assert res.iloc[0]['signal_level'] in ["WARM", "HOT", "EXTREME"]
    assert res.iloc[0]['label'] == "deepseek"
    assert "detail" in res.columns

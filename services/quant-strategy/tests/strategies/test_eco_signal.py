import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.strategies.eco_signal_strategy import EcoSignalStrategy

def generate_mock_raw_data(days=40, spike_at_end=False) -> pd.DataFrame:
    """生成连续 N 天的稳态或者末端暴涨记录的数据"""
    base_date = datetime(2026, 1, 1)
    data = []
    
    for i in range(days):
        # 稳定形态的假数据
        pr_acc = 5
        commits = 10
        issue_hrs = 24.0
        stars = 20
        contribs = 5
        
        # 如果要求末期暴涨，仅最后 1 天进行极值干预以确保在 30 天滑动窗口中其 Z-score 可以突破 3 Sigma
        if spike_at_end and i == days - 1:
            pr_acc = 50
            commits = 120    # 激增
            issue_hrs = 2.0  # 响应激增 (越小越快)
            stars = 500
            contribs = 100
            
        data.append({
            "collect_time": base_date + timedelta(days=i),
            "label": "test_eco",
            "org": "test_org",
            "repo": "test_repo",
            "pr_merged_acceleration": pr_acc,
            "commit_count_7d": commits,
            "issue_close_median_hours": issue_hrs,
            "star_delta_7d": stars,
            "contributor_count_30d": contribs
        })
        
    return pd.DataFrame(data)

def test_eco_signal_neutral():
    """测试平稳时期不应产生非 NEUTRAL 的杂音"""
    df = generate_mock_raw_data(days=40, spike_at_end=False)
    strategy = EcoSignalStrategy(window_size=30)
    
    result = strategy.calculate_signals(df)
    
    # 最后几天的状态由于标准差是 0, numpy where 保护应该会使其 Z-score 为 0.0，
    # 按照阈值 Z < 1.0 的情况均分类为 NEUTRAL
    assert result.iloc[-1]["signal_level"] == "NEUTRAL"
    assert result.iloc[-1]["composite_z_score"] == 0.0

def test_eco_signal_extreme_spike():
    """测试经过30天平稳积累下的均值与标准差能够在突增时映射为 EXTREME"""
    df = generate_mock_raw_data(days=40, spike_at_end=True)
    
    # 设定平稳期的波动作使得拥有标准差，否则标准差为 0 计算 Z=0
    # 我们在前置故意做少量噪声（引入标准差 > 0）
    noise = np.random.normal(0, 1, 40)
    df["commit_count_7d"] = df["commit_count_7d"] + noise
    
    strategy = EcoSignalStrategy(window_size=30)
    result = strategy.calculate_signals(df)
    
    # 最后一天的评级应大幅突破均值，导致 Z >= 3 进而判断为 EXTREME
    latest_signal = result.iloc[-1]
    
    assert latest_signal["signal_level"] == "EXTREME"
    assert latest_signal["composite_z_score"] > 3.0
    
def test_eco_signal_dominant_factor():
    """测试谁提供最强动量，主导要素 (dominant_factor) 就是谁"""
    df = generate_mock_raw_data(days=40, spike_at_end=False)
    
    # 给初始施加轻微噪声带来均值/方差基底
    df["star_delta_7d"] = df["star_delta_7d"] + np.random.normal(0, 5, 40)
    df["issue_close_median_hours"] = df["issue_close_median_hours"] + np.random.normal(0, 5, 40)
    df["commit_count_7d"] = df["commit_count_7d"] + np.random.normal(0, 2, 40)
    
    # 强行拉爆 momentum 源的一员 (最后一天)
    df.loc[39, "commit_count_7d"] += 2000
    
    strategy = EcoSignalStrategy(window_size=30)
    result = strategy.calculate_signals(df)
    
    latest_signal = result.iloc[-1]
    
    # Z 分数必然被 momentum 拉穿，由于仅拉单因素，平均 Z 分数极限约 1.79，因此预期为 WARM 以上即可
    assert latest_signal["signal_level"] in ["WARM", "HOT", "EXTREME"]
    assert latest_signal["dominant_factor"] == "MOMENTUM"

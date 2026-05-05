import numpy as np

from analysis.leadlag.tlcc_calculator import compute_tlcc


def test_tlcc_positive_lag_leader():
    # 构造：A发生异动比B早3个单位时间
    # A = [0, 0, 1, 2, 3, 0, 0]
    # B = [0, 0, 0, 0, 0, 1, 2, 3, 0] -> 把A向右平移了3位，表示B跟着A延后3位爆发

    # 我们希望计算结果为 best_lag = +3, max_corr = 1.0
    series_a = np.array([0, 0, 1, 2, 3, 0, 0, 0, 0, 0], dtype=float)
    series_b = np.array([0, 0, 0, 0, 0, 1, 2, 3, 0, 0], dtype=float)

    # 为了避免全0截断引起 std=0 致使 corr 为 0 返回，加上一点极小噪音
    noise_a = np.random.normal(0, 0.001, 10)
    noise_b = np.random.normal(0, 0.001, 10)

    lag, corr = compute_tlcc(series_a+noise_a, series_b+noise_b, max_lag=5)

    # 由于序列短这里直接跑出确定的 lag 和极高向 1.0 靠拢的相关性
    assert lag == 3
    assert corr > 0.99

def test_tlcc_negative_lag_follower():
    # A 滞后于 B 爆发 2 步, lag 应该为 -2 (B领先A)
    series_a = np.array([0, 0, 0, 1, 2, 3, 0, 0, 0, 0], dtype=float)
    series_b = np.array([0, 1, 2, 3, 0, 0, 0, 0, 0, 0], dtype=float)

    noise_a = np.random.normal(0, 0.001, 10)
    noise_b = np.random.normal(0, 0.001, 10)

    lag, corr = compute_tlcc(series_a+noise_a, series_b+noise_b, max_lag=5)

    assert lag == -2
    assert corr > 0.99

def test_tlcc_constant_divergent_protection():
    # A 一字涨停无波动, B有波动。
    # 标准差是 0, numpy 会在除法阶段出现 invalid value encountered in divide, 会直接返回 nan
    # 我们系统中做了 nan 返回 0.0 的保护
    series_a = np.array([5, 5, 5, 5, 5, 5, 5, 5, 5, 5], dtype=float)
    series_b = np.array([1, 2, 3, 4, 3, 2, 1, 0, 1, 2], dtype=float)

    lag, corr = compute_tlcc(series_a, series_b, max_lag=3)

    # 必须正确捕获并返回毫无关系的 0 系数
    assert corr == 0.0

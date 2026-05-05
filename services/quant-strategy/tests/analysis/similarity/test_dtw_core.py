import numpy as np

from analysis.similarity.dtw_core import dtw_distance_with_window


def test_dtw_exact_match():
    """测试完全相同序列距离应为0"""
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    dist = dtw_distance_with_window(a, b, window=2)
    assert dist == 0.0

def test_dtw_shifted_sequence():
    """测试发生时移但仍有相似模式的序列，DTW必须比曼哈顿/欧几里得距离能够更好对齐波形"""
    # a 为正常波形，b 比 a 滞后了两拍
    a = np.array([0, 0, 1, 2, 3, 2, 1, 0, 0, 0], dtype=float)
    b = np.array([0, 0, 0, 0, 1, 2, 3, 2, 1, 0], dtype=float)

    dist_with_dtw = dtw_distance_with_window(a, b, window=3)

    # 手动算个绝对差异成本
    dist_abs = np.sum(np.abs(a - b)) / (len(a) * 2)
    # 因为 DTW 能够扭曲匹配，导致成本大幅降低
    assert dist_with_dtw < dist_abs

def test_dtw_large_shift_exceeds_window():
    """当波形偏移大于限制窗口 Sakoe-Chiba 时，无法对齐"""
    a = np.array([0, 1, 2, 0, 0, 0, 0, 0, 0, 0], dtype=float)
    b = np.array([0, 0, 0, 0, 0, 0, 0, 1, 2, 0], dtype=float)

    # 窗口足够大可以对齐
    dist_large_win = dtw_distance_with_window(a, b, window=8)

    # 极小窗口无法对齐到真实高点
    dist_small_win = dtw_distance_with_window(a, b, window=2)

    assert dist_small_win > dist_large_win

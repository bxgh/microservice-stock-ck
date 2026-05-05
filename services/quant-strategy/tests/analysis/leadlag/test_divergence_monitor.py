import numpy as np

from analysis.leadlag.divergence_monitor import (
    TrendPhase,
    classify_trend_phase,
    compute_divergence,
)


def test_compute_divergence_steady():
    # 3 只股票的一致性走势 (平稳)
    returns = {
        "A": np.array([0.1, 0.2, 0.1, 0.2, 0.1], dtype=float),
        "B": np.array([0.1, 0.2, 0.1, 0.2, 0.1], dtype=float),
        "C": np.array([0.1, 0.2, 0.1, 0.2, 0.1], dtype=float)
    }

    div = compute_divergence(["A", "B", "C"], returns, window=3)

    # 股票之间毫无差异，横截面的 std 应该全为近乎 0
    assert len(div) == 5
    assert np.all(div < 1e-5)

def test_classify_trend_phase_dissolution():
    # 给定历史大波段从 0 到 10 都有
    history = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)

    # p80 在 8.2，如果当前分歧高达 9.5，说明正在瓦解期
    phase = classify_trend_phase(current_divergence=9.5, history_divergence=history)
    assert phase == TrendPhase.DISSOLUTION

    # p20 在 2.8，如果当前分歧降到 1.5，说明正在形成期
    phase = classify_trend_phase(current_divergence=1.5, history_divergence=history)
    assert phase == TrendPhase.FORMATION

    # 位于 5.0，应该是在稳步攀爬
    phase = classify_trend_phase(current_divergence=5.0, history_divergence=history)
    assert phase == TrendPhase.STEADY

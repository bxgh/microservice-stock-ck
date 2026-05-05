"""
增量相似度引擎单元测试
注意：Redis 相关的集成测试需在真实环境运行，此处只测 `_detect_changed_stocks` 核心逻辑
"""
from unittest.mock import MagicMock

import numpy as np

from analysis.similarity.incremental_engine import IncrementalSimilarityEngine


def _make_engine():
    """构造一个不依赖真实 Redis 的测试引擎"""
    mock_baseline = MagicMock()
    mock_cache = MagicMock()
    return IncrementalSimilarityEngine(
        baseline_engine=mock_baseline,
        cache_manager=mock_cache,
        change_threshold=0.5,
    )


def test_detect_changed_stocks_identifies_new_stocks():
    """没有前日缓存的股票应被标记为「变化」"""
    engine = _make_engine()

    today_features = {
        "000001": np.ones(240),
        "000002": np.ones(240) * 0.5,
    }
    # 所有昨日缓存皆为 None（新股 or 无缓存）
    yesterday_fingerprints = {"000001": None, "000002": None}

    changed = engine._detect_changed_stocks(
        yesterday_fingerprints, today_features, ["000001", "000002"]
    )

    assert "000001" in changed
    assert "000002" in changed


def test_detect_changed_stocks_filters_stable_stocks():
    """行为相同的股票不应被标记为变化"""
    engine = _make_engine()

    stable_vec = np.zeros(240)

    today_features = {
        "600000": stable_vec + 0.01,  # 仅微小扰动
        "300001": stable_vec + 0.01,
    }
    # 昨日向量相同
    yesterday_fingerprints = {
        "600000": stable_vec.copy(),
        "300001": stable_vec.copy(),
    }

    changed = engine._detect_changed_stocks(
        yesterday_fingerprints, today_features, ["600000", "300001"]
    )

    # 扰动量 0.01 在 240 维下的 L2 = 0.01，远低于阈值 0.5
    assert "600000" not in changed
    assert "300001" not in changed


def test_detect_changed_stocks_finds_volatile_stock():
    """行为发生显著变化的股票应被识别"""
    engine = _make_engine()

    base = np.zeros(240)
    volatilized = np.ones(240) * 2.0  # L2 = 2.0 * sqrt(240) >> 0.5

    today_features = {
        "600036": volatilized,
        "000001": base,  # 保持不变
    }
    yesterday_fingerprints = {
        "600036": base.copy(),
        "000001": base.copy(),
    }

    changed = engine._detect_changed_stocks(
        yesterday_fingerprints, today_features, ["600036", "000001"]
    )

    assert "600036" in changed
    assert "000001" not in changed

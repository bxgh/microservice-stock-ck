
import numpy as np
import pytest

from analysis.similarity.engine import SimilarityEngine
from core.models.similarity_matrix import SimilarityMatrix


@pytest.fixture
def mock_features():
    """造一个微缩版的股票池特征矩阵"""
    # 5 只股票，各包含 10维（代替240维）特征

    # 构建出两只几乎相同的数据（000001 和 000002）
    v1 = np.array([1, 2, 3, 4, 5, 4, 3, 2, 1, 0], dtype=float)
    v2 = np.array([1, 2, 3, 4, 5, 4, 3, 2, 1, 2], dtype=float)  # 极度相似

    # 构造一只波动趋势反向或者随机的
    v3 = np.array([5, 4, 3, 2, 1, 0, 1, 2, 3, 4], dtype=float)

    # 构造一只时移的 (000004 比较像 000001 的滞后版)
    v4 = np.array([0, 1, 2, 3, 4, 5, 4, 3, 2, 1], dtype=float)

    # 不相关
    v5 = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=float)

    features = {
        "000001.SZ": v1,
        "000002.SZ": v2,
        "000003.SZ": v3,
        "000004.SZ": v4,
        "000005.SZ": v5,
    }

    return features


@pytest.mark.asyncio
async def test_engine_end_to_end_flow(mock_features):
    """测试整个引擎是否能够正确运行到最后，多进程是否能够正确汇总"""

    engine = SimilarityEngine(max_workers=2, dtw_window=3)

    # 为了测试目的，将 prefilter 放宽，确保至少能出来几对组合
    matrix: SimilarityMatrix = await engine.compute_similarity_all(
        features_a=mock_features,
        features_b=mock_features,  # 为了简单用同一套特征测试
        features_c=mock_features,
        prefilter_top_k=0.5, # 放宽粗筛让更多组合进入阶段二
        weights=(0.5, 0.3, 0.2)
    )

    assert isinstance(matrix, SimilarityMatrix)
    # 因为总共才 5只股票，全排列 10对组合。粗筛 0.5 之后应该剩余一部分
    assert len(matrix.stock_pairs) > 0
    assert len(matrix.distances) == len(matrix.stock_pairs)

    # 检查是否有最像的(000001, 000002)存在
    has_closest = False
    for pair in matrix.stock_pairs:
        if pair == ("000001.SZ", "000002.SZ") or pair == ("000002.SZ", "000001.SZ"):
            has_closest = True
            break

    assert has_closest, "Euclidean pre-filter missed the most obvious pair!"

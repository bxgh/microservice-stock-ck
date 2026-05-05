import numpy as np

from analysis.clustering.graph_builder import build_similarity_graph
from analysis.clustering.noise_filters import (
    filter_industry_homogeneity,
    filter_market_beta_clusters,
    filter_small_clusters,
)
from core.models.similarity_matrix import SimilarityMatrix


def test_filter_small_clusters():
    # 模拟 3 个 cluster:
    # 0 包含 4 个成员 -> 保留
    # 1 包含 2 个成员 -> 剔除
    # 2 包含 1 个成员 -> 剔除
    clusters = {
        "A": 0, "B": 0, "C": 0, "D": 0,
        "E": 1, "F": 1,
        "G": 2
    }

    result = filter_small_clusters(clusters, min_size=3)
    assert len(result) == 4
    assert set(result.keys()) == {"A", "B", "C", "D"}

def test_filter_market_beta_clusters():
    # 模拟两组序列，一组完全追踪基准，一组差异较大
    benchmark = np.array([1, 2, 3, 4, 5], dtype=float)

    # 追踪大盘 (corr = 1.0)
    stock_returns = {
        "A": np.array([1, 2, 3, 4, 5], dtype=float),
        "B": np.array([1.1, 2.1, 2.9, 4.2, 4.9], dtype=float), # 高度相关
        # 不追踪大盘 (相关性极低)
        "C": np.array([1, 5, 2, 4, 3], dtype=float), # 杂乱无章
        "D": np.array([2, 5, 1, 5, 2], dtype=float)
    }

    clusters = {
        "A": 0, "B": 0,
        "C": 1, "D": 1
    }

    result = filter_market_beta_clusters(clusters, stock_returns, benchmark, correlation_threshold=0.9)
    # 群组 0 相关性应 > 0.9，被剔除
    # 群组 1 走势震荡无章，被保留
    assert "A" not in result
    assert "C" in result
    assert "D" in result

def test_filter_industry_homogeneity():
    clusters = {
        "A": 0, "B": 0, "C": 0, "D": 0,  # 群组0：全是软件
        "E": 1, "F": 1, "G": 1, "H": 1   # 群组1：涵盖3个行业
    }

    industry_map = {
        "A": "软件开发", "B": "软件开发", "C": "软件开发", "D": "软件开发",
        "E": "汽车整车", "F": "生物制品", "G": "光伏设备", "H": "汽车整车"
    }

    # 超过 80% 同质化即被剔除
    result = filter_industry_homogeneity(clusters, industry_map, homogeneity_threshold=0.8)

    # 群组0 (100% 同质化) 应该被删除
    assert "A" not in result
    # 群组1 (最高 50% 汽车整车) 应该保留
    assert "E" in result

def test_graph_builder_sparsity():
    # 测试能否自适应地选取符合阈值的强关系
    pairs = [("A", "B"), ("A", "C"), ("B", "C"), ("C", "D")]
    # 其中一对距离是 0.1，其他都是 0.9（不相似）
    distances = np.array([0.1, 0.9, 0.95, 0.99])

    matrix = SimilarityMatrix(stock_pairs=pairs, distances=distances)

    # 选取前 25% (因为共有 4 条边，按分位数算法会插值在 0.1 和 0.9 之间得到 0.7)
    g_graph, threshold = build_similarity_graph(matrix, sparsity_percentile=0.25)

    assert threshold == 0.7
    # 网络应该只包含 1 条边
    assert g_graph.number_of_edges() == 1
    # 且包含 2 个节点
    assert g_graph.number_of_nodes() == 2
    assert g_graph.has_edge("A", "B")

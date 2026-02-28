import logging

import networkx as nx  # type: ignore
import numpy as np

from src.core.models.similarity_matrix import SimilarityMatrix

logger = logging.getLogger(__name__)

def build_similarity_graph(
    similarity_matrix: SimilarityMatrix,
    sparsity_percentile: float = 0.05
) -> tuple[nx.Graph, float]:
    """
    根据阶段一引擎输出的相似度矩阵构建无向加权图。
    通过动态计算阈值（如距离分布的前5%）来稀疏化网络，
    避免全连接图带来的巨大计算量及噪音聚集，仅保留强关联边。

    Args:
        similarity_matrix: SimilarityMatrix 实例，包含配对及其对应距离
        sparsity_percentile: 稀疏化比例控制，0.05 代表只取距离最小的前5%边

    Returns:
        g_graph: 裁剪后的 networkx 无向加权图
        threshold: 内部计算得出的绝对距离截断阈值
    """
    g_graph = nx.Graph()

    distances = similarity_matrix.distances
    if len(distances) == 0:
        logger.warning("Empty similarity matrix provided. Returning empty graph.")
        return g_graph, 0.0

    # 计算距离截断阈值，获取最短的前X%作为有效边
    # quantile 期望输入的是分布的位置，值越小代表DTW扭曲距离越近，即越相似
    threshold = float(np.quantile(distances, sparsity_percentile))
    logger.info(f"Graph builder dynamic distance threshold (bottom {sparsity_percentile*100}%): {threshold:.4f}")

    valid_edges = 0
    for pair, dist in zip(similarity_matrix.stock_pairs, distances, strict=False):
        dist_float = float(dist)
        if dist_float <= threshold:
            # 距离越小，代表越集中、相似度权重越高
            # 加 1e-6 极小数避免重合时除以零异常
            weight = 1.0 / (dist_float + 1e-6)
            stock_a, stock_b = pair
            g_graph.add_edge(stock_a, stock_b, weight=weight, distance=dist_float)
            valid_edges += 1

    logger.info(f"Graph built with {g_graph.number_of_nodes()} active nodes and {valid_edges} reliable edges.")
    return g_graph, threshold

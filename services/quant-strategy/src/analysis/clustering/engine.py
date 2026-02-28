import logging
from collections import defaultdict

import numpy as np

from src.analysis.clustering.graph_builder import build_similarity_graph
from src.analysis.clustering.leiden_detector import detect_communities_leiden
from src.analysis.clustering.noise_filters import (
    filter_industry_homogeneity,
    filter_low_turnover_clusters,
    filter_market_beta_clusters,
    filter_small_clusters,
)
from src.core.models.cluster import FundCluster
from src.core.models.similarity_matrix import SimilarityMatrix

logger = logging.getLogger(__name__)

class ClusteringEngine:
    """资金团伙聚类与去噪引擎"""

    def __init__(
        self,
        sparsity_limit: float = 0.05,
        resolution: float = 1.0,
        beta_limit: float = 0.9,
        ind_limit: float = 0.8,
        min_cluster_size: int = 3,
        min_turnover: float = 0.02
    ):
        self.sparsity = sparsity_limit
        self.resolution = resolution
        self.beta_limit = beta_limit
        self.ind_limit = ind_limit
        self.min_size = min_cluster_size
        self.min_turnover = min_turnover

    def run_clustering(
        self,
        sim_matrix: SimilarityMatrix,
        stock_returns: dict[str, np.ndarray],
        benchmark_returns: np.ndarray,
        stock_industry: dict[str, str],
        turnover_data: dict[str, float]
    ) -> list[FundCluster]:
        """
        执行完整的社区发现和去躁端到端管线
        """
        logger.info("Step 1: Building adaptive sparse graph from similarity matrix...")
        g_graph, threshold = build_similarity_graph(sim_matrix, sparsity_percentile=self.sparsity)

        if g_graph.number_of_nodes() == 0:
            logger.warning("Graph is empty. Terminating clustering early.")
            return []

        logger.info(f"Step 2: Performing Leiden Community Detection (res={self.resolution})...")
        raw_clusters = detect_communities_leiden(g_graph, resolution=self.resolution)

        logger.info(f"Leiden found raw clusters involving {len(raw_clusters)} stocks.")

        logger.info("Step 3: Applying deep noise filtration pipeline...")
        # L1: 防火墙 - 滤除随机巧合小集群
        c1 = filter_small_clusters(raw_clusters, min_size=self.min_size)

        # L2: 防火墙 - 滤除僵尸或停牌股聚集区
        c2 = filter_low_turnover_clusters(c1, turnover_data, min_avg_turnover=self.min_turnover)

        # L3: 防火墙 - 大盘 Beta 中和（极严格）
        c3 = filter_market_beta_clusters(
            c2,
            stock_returns,
            benchmark_returns,
            correlation_threshold=self.beta_limit
        )

        # L4: 防火墙 - 行业板块轮动驱逐（极严格）
        final_clusters_map = filter_industry_homogeneity(
            c3,
            stock_industry,
            homogeneity_threshold=self.ind_limit
        )

        logger.info(f"Filtration complete. Surviving stocks: {len(final_clusters_map)}")

        return self._build_cluster_models(final_clusters_map, stock_industry, turnover_data)

    def _build_cluster_models(
        self,
        filtered_map: dict[str, int],
        stock_industry: dict[str, str],
        turnover_data: dict[str, float]
    ) -> list[FundCluster]:
        """将股票字典聚合为具有统计特性的 FundCluster 模型实例库"""
        cid_groups = defaultdict(list)
        for stock, cid in filtered_map.items():
            cid_groups[cid].append(stock)

        results = []
        for cid, stocks in cid_groups.items():
            # 统计行业占比
            ind_counts: dict[str, int] = defaultdict(int)
            total = len(stocks)
            for s in stocks:
                if s in stock_industry:
                    ind_counts[stock_industry[s]] += 1

            dominant_ind = "Unknown"
            dom_ratio = 0.0
            if ind_counts:
                dominant_ind = max(ind_counts, key=lambda k: ind_counts[k])
                dom_ratio = ind_counts[dominant_ind] / total

            # 计算平均换手
            valid_to = [turnover_data[s] for s in stocks if s in turnover_data]
            avg_to = float(np.mean(valid_to)) if valid_to else 0.0

            fc = FundCluster(
                cluster_id=cid,
                stock_codes=stocks,
                member_count=total,
                dominant_industry=dominant_ind,
                industry_ratio=float(dom_ratio),
                avg_turnover=avg_to,
                beta_correlation=0.0 # Detailed recalculation can be done if requested downstream
            )
            results.append(fc)

        return results

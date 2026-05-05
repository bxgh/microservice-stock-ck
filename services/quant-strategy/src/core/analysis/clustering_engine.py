import logging

import community as community_louvain
import igraph as ig
import leidenalg
import networkx as nx
import numpy as np
import pandas as pd

from adapters.clickhouse_loader import ClickHouseLoader

logger = logging.getLogger(__name__)

class ClusteringEngine:
    """
    社区发现与聚类引擎 (Story 003.02)
    负责将相似股票划分为"资金团"，并过滤噪音。
    """
    def __init__(self, loader: ClickHouseLoader | None = None):
        self.loader = loader if loader else ClickHouseLoader()

    async def initialize(self):
        await self.loader.initialize()
        logger.info("✅ ClusteringEngine initialized")

    def build_similarity_graph(
        self,
        stock_codes: list[str],
        similarity_results: dict[tuple[int, int], float],
        distance_threshold: float | None = None,
        percentile: float = 5.0
    ) -> nx.Graph:
        """
        构建相似度图
        """
        G = nx.Graph()
        # 添加节点
        for i, code in enumerate(stock_codes):
            G.add_node(i, code=code)

        # 确定阈值
        distances = list(similarity_results.values())
        if not distances:
            return G

        if distance_threshold is None:
            distance_threshold = np.percentile(distances, percentile)
            logger.info(f"Using adaptive distance threshold: {distance_threshold:.4f} (p={percentile})")

        # 添加边
        for (i, j), dist in similarity_results.items():
            if dist <= distance_threshold:
                weight = 1.0 / (1.0 + dist)
                G.add_edge(i, j, weight=weight, distance=dist)

        logger.info(f"✅ Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def detect_communities(self, G: nx.Graph, method: str = "leiden", resolution: float = 1.0) -> dict[int, int]:
        """
        社区发现
        method: "louvain" 或 "leiden"
        """
        if G.number_of_edges() == 0:
            return {node: node for node in G.nodes()}

        if method == "louvain":
            partition = community_louvain.best_partition(
                G,
                weight='weight',
                resolution=resolution,
                random_state=42
            )
        else:
            # 使用 Leiden (更稳定)
            # 转为 igraph
            ig_graph = ig.Graph.from_networkx(G)
            # Leiden 需要正权重
            # RBConfigurationVertexPartition 对应于带 resolution 的 Modularity
            partition_leiden = leidenalg.find_partition(
                ig_graph,
                leidenalg.RBConfigurationVertexPartition,
                weights=ig_graph.es['weight'],
                resolution_parameter=resolution,
                seed=42
            )
            partition = dict(enumerate(partition_leiden.membership))

        num_clusters = len(set(partition.values()))
        logger.info(f"✅ Detected {num_clusters} communities using {method}")
        return partition

    async def filter_noise_clusters(
        self,
        partition: dict[int, int],
        stock_codes: list[str],
        returns_dict: dict[str, np.ndarray],
        benchmark_returns: np.ndarray,
        min_size: int = 3,
        market_corr_limit: float = 0.9,
        turnover_dict: dict[str, float] | None = None,
        min_turnover: float = 0.01,
        industry_dict: dict[str, str] | None = None,
        industry_homo_limit: float = 0.8
    ) -> dict[int, list[str]]:
        """
        噪音过滤
        1. 成员数过滤
        2. 大盘 Beta 中和
        3. 换手率过滤 (低换手过滤僵尸股)
        4. 行业同质化标记 (可选，非物理过滤，仅标记或记录)
        """
        clusters = {}
        for node_idx, cluster_id in partition.items():
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(stock_codes[node_idx])

        filtered_clusters = {}

        for cid, members in clusters.items():
            # 1. 规模检查
            if len(members) < min_size:
                continue

            # 2. 换手率检查
            if turnover_dict:
                avg_turnover = np.mean([turnover_dict.get(m, 0) for m in members])
                if avg_turnover < min_turnover:
                    logger.debug(f"Cluster {cid} skipped: low turnover {avg_turnover:.4f}")
                    continue

            # 3. 大盘 Beta 检查
            cluster_series = [returns_dict[m] for m in members if m in returns_dict]
            if not cluster_series:
                continue

            avg_cluster_return = np.mean(cluster_series, axis=0)

            if len(benchmark_returns) == len(avg_cluster_return):
                correlation = np.corrcoef(avg_cluster_return, benchmark_returns)[0, 1]
                if abs(correlation) > market_corr_limit:
                    logger.debug(f"Cluster {cid} skipped: high market correlation ({correlation:.2f})")
                    continue

            # 4. 行业同质化检查 (仅日志记录，不强制过滤)
            if industry_dict:
                industries = [industry_dict.get(m, "unknown") for m in members]
                main_industry = pd.Series(industries).value_counts().iloc[0]
                ratio = main_industry / len(members)
                if ratio > industry_homo_limit:
                    logger.debug(f"Cluster {cid} is highly industry-homogenous ({ratio:.2f})")

            filtered_clusters[cid] = members

        logger.info(f"✅ Noise filtering done. Kept {len(filtered_clusters)} clusters")
        return filtered_clusters

    def evaluate_stability(self, current: list[set[str]], past: list[set[str]]) -> list[tuple[int, float]]:
        """计算 Jaccard 稳定性"""
        stability_results = []
        for i, curr in enumerate(current):
            max_jaccard = max([len(curr & p) / len(curr | p) for p in past] + [0])
            stability_results.append((i, max_jaccard))
        return stability_results

    async def close(self):
        await self.loader.close()


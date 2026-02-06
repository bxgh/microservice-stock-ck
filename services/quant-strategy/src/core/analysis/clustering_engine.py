
import logging
import numpy as np
import pandas as pd
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional
import community as community_louvain
from adapters.clickhouse_loader import ClickHouseLoader

logger = logging.getLogger(__name__)

class ClusteringEngine:
    """
    社区发现与聚类引擎 (Story 003.02)
    负责将相似股票划分为"资金团"，并过滤噪音。
    """
    def __init__(self, loader: Optional[ClickHouseLoader] = None):
        self.loader = loader if loader else ClickHouseLoader()

    async def initialize(self):
        await self.loader.initialize()
        logger.info("✅ ClusteringEngine initialized")

    def build_similarity_graph(
        self, 
        stock_codes: List[str], 
        similarity_results: Dict[Tuple[int, int], float],
        distance_threshold: Optional[float] = None,
        percentile: float = 5.0
    ) -> nx.Graph:
        """
        构建相似度图
        """
        G = nx.Graph()
        # 添加节点
        for i, code in enumerate(stock_codes):
            G.add_node(i, code=code)

        # 确定阈值 (如果未提供，默认按 percentile 计算)
        distances = list(similarity_results.values())
        if not distances:
            return G
            
        if distance_threshold is None:
            distance_threshold = np.percentile(distances, percentile)
            logger.info(f"Using adaptive distance threshold: {distance_threshold:.4f} (p={percentile})")

        # 添加边
        for (i, j), dist in similarity_results.items():
            if dist <= distance_threshold:
                # 权重公式: 1 / (1 + dist)
                weight = 1.0 / (1.0 + dist)
                G.add_edge(i, j, weight=weight, distance=dist)

        logger.info(f"✅ Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def detect_communities(self, G: nx.Graph, resolution: float = 1.0) -> Dict[int, int]:
        """
        使用 Louvain 算法进行社区发现
        """
        if G.number_of_edges() == 0:
            return {node: node for node in G.nodes()}
            
        partition = community_louvain.best_partition(
            G, 
            weight='weight', 
            resolution=resolution,
            random_state=42 # 保证结果确定性
        )
        
        num_clusters = len(set(partition.values()))
        logger.info(f"✅ Detected {num_clusters} communities using Louvain")
        return partition

    async def filter_noise_clusters(
        self, 
        partition: Dict[int, int], 
        stock_codes: List[str],
        returns_dict: Dict[str, np.ndarray],
        benchmark_returns: np.ndarray,
        min_size: int = 3,
        market_corr_limit: float = 0.9
    ) -> Dict[int, List[str]]:
        """
        噪音过滤
        1. 成员数过少过滤
        2. 大盘 Beta 中和 (剔除与大盘高度相关的簇)
        """
        # 1. 分组
        clusters = {}
        for node_idx, cluster_id in partition.items():
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(stock_codes[node_idx])

        filtered_clusters = {}
        
        for cid, members in clusters.items():
            # 规则 1: 成员数量
            if len(members) < min_size:
                logger.debug(f"Cluster {cid} skipped: size {len(members)} < {min_size}")
                continue
            
            # 规则 2: 大盘 Beta 检查
            # 计算簇的平均收益率序列 (240维)
            cluster_series = []
            for m in members:
                if m in returns_dict:
                    cluster_series.append(returns_dict[m])
            
            if not cluster_series:
                continue
                
            avg_cluster_return = np.mean(cluster_series, axis=0)
            
            # 计算与 benchmark 的相关性
            if len(benchmark_returns) == len(avg_cluster_return):
                correlation = np.corrcoef(avg_cluster_return, benchmark_returns)[0, 1]
                if abs(correlation) > market_corr_limit:
                    logger.debug(f"Cluster {cid} skipped: high market correlation ({correlation:.2f})")
                    continue
                else:
                    logger.debug(f"Cluster {cid} passed market check: corr={correlation:.4f}")
            
            filtered_clusters[cid] = members

        logger.info(f"✅ Noise filtering done. Kept {len(filtered_clusters)} clusters (from {len(clusters)})")
        return filtered_clusters

    def evaluate_stability(
        self, 
        current_clusters: List[Set[str]], 
        past_clusters: List[Set[str]]
    ) -> List[Tuple[int, float]]:
        """
        计算跨日稳定性 (Jaccard Index)
        """
        stability_results = []
        for i, curr in enumerate(current_clusters):
            max_jaccard = 0.0
            for past in past_clusters:
                intersection = len(curr.intersection(past))
                union = len(curr.union(past))
                jaccard = intersection / union if union > 0 else 0
                max_jaccard = max(max_jaccard, jaccard)
            stability_results.append((i, max_jaccard))
        
        return stability_results

    async def close(self):
        await self.loader.close()


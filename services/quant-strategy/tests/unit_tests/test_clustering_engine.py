
import pytest
import numpy as np
import networkx as nx
from core.analysis.clustering_engine import ClusteringEngine

class TestClusteringEngine:
    @pytest.fixture
    def engine(self):
        return ClusteringEngine()

    def test_build_similarity_graph(self, engine):
        """测试构图逻辑"""
        stock_codes = ["000001", "000002", "600519", "600036"]
        # 给定 0-1, 2-3 比较近
        similarity_results = {
            (0, 1): 0.1, # dist=0.1 -> weight=0.91
            (2, 3): 0.15,
            (0, 2): 0.8,
            (1, 3): 0.9
        }
        
        # 强制设置阈值为 0.2
        G = engine.build_similarity_graph(stock_codes, similarity_results, distance_threshold=0.2)
        
        assert G.number_of_nodes() == 4
        assert G.number_of_edges() == 2 # 仅 (0,1) 和 (2,3)
        assert G.has_edge(0, 1)
        assert G.has_edge(2, 3)
        assert G[0][1]['weight'] == pytest.approx(1.0 / 1.1)

    def test_detect_communities(self, engine):
        """测试 Louvain 聚类"""
        G = nx.Graph()
        # 创建两个明显的团
        # 团 1: 0, 1, 2
        G.add_edge(0, 1, weight=1.0)
        G.add_edge(1, 2, weight=1.0)
        G.add_edge(0, 2, weight=1.0)
        # 团 2: 3, 4, 5
        G.add_edge(3, 4, weight=1.0)
        G.add_edge(4, 5, weight=1.0)
        G.add_edge(3, 5, weight=1.0)
        
        partition = engine.detect_communities(G)
        
        assert len(set(partition.values())) == 2
        # 同一簇的应该 ID 相同
        assert partition[0] == partition[1] == partition[2]
        assert partition[3] == partition[4] == partition[5]
        assert partition[0] != partition[3]

    @pytest.mark.asyncio
    async def test_filter_noise_clusters(self, engine):
        """测试噪音过滤 (Size & Beta)"""
        partition = {0: 1, 1: 1, 2: 1, 3: 2, 4: 2} 
        # Cluster 1 (size 3), Cluster 2 (size 2)
        stock_codes = ["S0", "S1", "S2", "S3", "S4"]
        
        # 模拟收益率序列 (240维)
        base = np.random.randn(240) * 0.01
        returns_dict = {
            "S0": base + np.random.randn(240) * 0.001,
            "S1": base + np.random.randn(240) * 0.001,
            "S2": base + np.random.randn(240) * 0.001,
            "S3": np.random.randn(240) * 0.01,
            "S4": np.random.randn(240) * 0.01,
        }
        # S0-S2 与市场高度正相关
        benchmark = base * 0.95 + np.random.randn(240) * 0.001
        
        # 预估:
        # Cluster 2 会因为 size < 3 被过滤
        # Cluster 1 会因为与大盘相关性过高被过滤
        filtered = await engine.filter_noise_clusters(
            partition, 
            stock_codes, 
            returns_dict, 
            benchmark,
            min_size=3,
            market_corr_limit=0.9
        )
        
        assert len(filtered) == 0

    def test_evaluate_stability(self, engine):
        """测试稳定性评估"""
        current = [{"A", "B", "C"}, {"D", "E"}]
        past = [{"A", "B", "C", "X"}, {"Y", "Z"}]
        
        results = engine.evaluate_stability(current, past)
        
        assert len(results) == 2
        # Cluster 0 ("A,B,C") 与 Past 0 ("A,B,C,X") 的 Jaccard 为 3/4 = 0.75
        assert results[0][1] == 0.75
        # Cluster 1 ("D,E") 与 Past 完全无交集
        assert results[1][1] == 0.0

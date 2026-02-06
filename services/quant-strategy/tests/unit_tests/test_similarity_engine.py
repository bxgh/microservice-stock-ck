
import pytest
import numpy as np
import asyncio
from core.analysis.similarity_engine import SimilarityEngine, _dtw_core

class TestSimilarityEngine:
    @pytest.fixture
    def engine(self):
        return SimilarityEngine(num_workers=2)

    def test_dtw_core_identity(self):
        """测试相同序列的 DTW 距离应为 0"""
        s1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        s2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = _dtw_core(s1, s2, window=5)
        assert dist == 0.0

    def test_dtw_core_shifted(self):
        """测试平移序列的 DTW 距离应小于直接比较"""
        # s1: [0, 1, 0, 0, 0]
        # s2: [0, 0, 1, 0, 0] (右移一位)
        s1 = np.zeros(10)
        s1[2] = 1.0
        s2 = np.zeros(10)
        s2[3] = 1.0
        
        dist_dtw = _dtw_core(s1, s2, window=2)
        dist_euclidean = np.sum(np.abs(s1 - s2))
        
        # DTW 应该能完美匹配这个平移，距离为 0
        assert dist_dtw == 0.0
        assert dist_euclidean > 0.0

    def test_euclidean_prefilter(self, engine):
        """测试欧式粗筛逻辑"""
        # 创建 5 只股票的特征 (240维)
        # 0 和 1 非常相似
        # 2, 3, 4 是噪音
        feat_a = np.random.randn(5, 240) * 0.1
        feat_a[1] = feat_a[0] + np.random.randn(240) * 0.01 
        
        feat_b = np.random.randn(5, 240) * 0.1
        feat_b[1] = feat_b[0] + np.random.randn(240) * 0.01
        
        feat_c = np.random.randn(5, 240) * 0.1
        feat_c[1] = feat_c[0] + np.random.randn(240) * 0.01
        
        # 预筛选保留前 10% (5*4/2 = 10 对，保留 1 对)
        candidates = engine.euclidean_prefilter(feat_a, feat_b, feat_c, top_k_percent=0.1)
        
        assert len(candidates) == 1
        # 应该是 (0, 1)
        assert candidates[0] == (0, 1)

    @pytest.mark.asyncio
    async def test_compute_dtw_parallel(self, engine):
        """测试并行计算流程"""
        feat_a = np.random.randn(10, 240)
        feat_b = np.random.randn(10, 240)
        feat_c = np.random.randn(10, 240)
        
        # 假定发现了 3 对候选
        candidates = [(0, 1), (2, 3), (4, 5)]
        
        results = await engine.compute_dtw_parallel(candidates, feat_a, feat_b, feat_c)
        
        assert len(results) == 3
        for pair in candidates:
            assert pair in results
            assert results[pair] >= 0.0
            
        await engine.close()

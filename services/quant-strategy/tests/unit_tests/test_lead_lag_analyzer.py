
import pytest
import numpy as np
import networkx as nx
from core.analysis.lead_lag_analyzer import LeadLagAnalyzer, TrendPhase

class TestLeadLagAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return LeadLagAnalyzer()

    def test_compute_tlcc_identity(self, analyzer):
        """测试同步序列"""
        s1 = np.random.randn(240)
        lag, corr = analyzer.compute_tlcc(s1, s1)
        assert lag == 0
        assert corr == pytest.approx(1.0)

    def test_compute_tlcc_lagged(self, analyzer):
        """测试有时滞的序列"""
        # s1 领先 s2 5 分钟
        s1 = np.random.randn(240)
        s2 = np.roll(s1, 5) # B 是 A 的右移
        # 注意: np.roll 会循环移动，但在我们的 TLCC 实现中，偏移是通过切片做的
        # 重新构造非循环偏移
        s1 = np.random.randn(240)
        s2 = np.zeros(240)
        s2[5:] = s1[:-5]
        
        # 对于 compute_tlcc(s1, s2):
        # 当 lag = 5 时, s1[:-5] 与 s2[5:] 比较, 这两者完全一致
        lag, corr = analyzer.compute_tlcc(s1, s2, max_lag=10)
        assert lag == 5
        assert corr > 0.9

    def test_build_lead_lag_graph(self, analyzer):
        """测试有向图构建"""
        stock_codes = ["Leader", "Follower"]
        s1 = np.random.randn(240)
        s2 = np.zeros(240)
        s2[5:] = s1[:-5]
        
        returns_dict = {
            "Leader": s1,
            "Follower": s2
        }
        
        G = analyzer.build_lead_lag_graph(stock_codes, returns_dict)
        
        # 现在方向是 Follower -> Leader
        assert G.has_edge("Follower", "Leader")
        assert G["Follower"]["Leader"]["lag"] == 5

    def test_identify_leader(self, analyzer):
        """测试龙头识别"""
        G = nx.DiGraph()
        # 2, 3 跟随 1 (1 是龙头)
        G.add_edge("2", "1", weight=1.0)
        G.add_edge("3", "1", weight=1.0)
        # 3 也跟随 2
        G.add_edge("3", "2", weight=0.8)
        
        leaders = analyzer.identify_leader(G)
        
        # 1 应该是最高排位，因为两个跟随者
        assert leaders[0][0] == "1"

    def test_compute_divergence(self, analyzer):
        """测试分歧度计算"""
        members = ["S1", "S2"]
        # S1, S2 完全一致 -> std 应为 0
        s = np.random.randn(240)
        returns_dict = {"S1": s, "S2": s}
        
        div = analyzer.compute_divergence(members, returns_dict, window=1)
        assert np.all(div == 0.0)

    def test_classify_trend_phase(self, analyzer):
        """测试趋势阶段分类"""
        history = np.linspace(0, 10, 100) # 0 to 10
        # p20 = 2, p80 = 8
        
        assert analyzer.classify_trend_phase(1.0, history) == TrendPhase.FORMATION
        assert analyzer.classify_trend_phase(5.0, history) == TrendPhase.STEADY
        assert analyzer.classify_trend_phase(9.0, history) == TrendPhase.DISSOLUTION

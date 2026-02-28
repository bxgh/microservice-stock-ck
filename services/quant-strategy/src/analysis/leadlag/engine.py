import logging

import numpy as np

from src.analysis.leadlag.divergence_monitor import classify_trend_phase, compute_divergence
from src.analysis.leadlag.pagerank_sorter import build_lead_lag_graph, identify_leader
from src.analysis.leadlag.tlcc_calculator import compute_tlcc
from src.core.models.cluster import FundCluster
from src.core.models.enhanced_cluster import EnhancedCluster
from src.core.models.enhanced_cluster import TrendPhase as EnhancedTrendPhase

logger = logging.getLogger(__name__)

class LeadLagAnalyzer:
    """微观战术龙头挖掘引擎 (Story 003.03)"""

    def __init__(
        self,
        max_lag: int = 15,
        min_corr: float = 0.5,
        min_lag: int = 2,
        div_window: int = 30
    ):
        self.max_lag = max_lag
        self.min_corr = min_corr
        self.min_lag = min_lag
        self.div_window = div_window

    def analyze_clusters(
        self,
        clusters: list[FundCluster],
        returns_data: dict[str, np.ndarray]
    ) -> list[EnhancedCluster]:
        """
        对传入的初筛资金聚落进行二次深加工，寻找龙头并诊断周期。
        """
        enhanced_results = []

        for c in clusters:
            try:
                enhanced_cluster = self._analyze_single_cluster(c, returns_data)
                if enhanced_cluster:
                    enhanced_results.append(enhanced_cluster)
            except Exception as e:
                logger.error(f"Error analyzing cluster #{c.cluster_id}: {str(e)}", exc_info=True)
                continue

        logger.info(f"Lead-Lag analysis complete. Yielded {len(enhanced_results)} enhanced clusters.")
        return enhanced_results

    def _analyze_single_cluster(
        self,
        cluster: FundCluster,
        returns_data: dict[str, np.ndarray]
    ) -> EnhancedCluster:

        stocks = cluster.stock_codes
        n = len(stocks)

        # 1. N^2 计算两两 TLCC
        tlcc_results: dict[tuple[str, str], tuple[int, float]] = {}
        for i in range(n):
            for j in range(i + 1, n):
                s_a, s_b = stocks[i], stocks[j]
                if s_a not in returns_data or s_b not in returns_data:
                    continue

                lag, corr = compute_tlcc(returns_data[s_a], returns_data[s_b], self.max_lag)
                tlcc_results[(s_a, s_b)] = (lag, corr)

        # 2. 定位龙头
        g_graph = build_lead_lag_graph(tlcc_results, self.min_corr, self.min_lag)
        leaders = identify_leader(g_graph)

        if leaders:
            top_leader, top_score = leaders[0]
        else:
            # 如果没查出明确跟随关系网络，首字母兜底 (极小情况由于流动性休眠无波动)
            top_leader = stocks[0] if stocks else "UNKNOWN"
            top_score = 0.0

        # 3. 计算群体分歧度阶段
        div_history = compute_divergence(stocks, returns_data, self.div_window)
        current_div = 0.0
        phase = EnhancedTrendPhase.STEADY

        if len(div_history) > 0 and not np.isnan(div_history[-1]):
            current_div = float(div_history[-1])
            raw_phase = classify_trend_phase(current_div, div_history)
            # Enum mapping
            phase = EnhancedTrendPhase(raw_phase.value)

        # 4. 组装并返回 Enhanced 实体
        return EnhancedCluster(
            cluster_id=cluster.cluster_id,
            stock_codes=cluster.stock_codes,
            member_count=cluster.member_count,
            dominant_industry=cluster.dominant_industry,
            leader_stock=top_leader,
            pagerank_score=top_score,
            current_divergence=current_div,
            trend_phase=phase
        )

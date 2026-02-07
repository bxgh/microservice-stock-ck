import logging
from enum import Enum

import networkx as nx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class TrendPhase(Enum):
    FORMATION = "合力形成期"
    STEADY = "稳定运行期"
    DISSOLUTION = "瓦解期"

class LeadLagAnalyzer:
    """
    龙头识别与趋势判定引擎 (Story 003.03)
    """
    def __init__(self):
        pass

    async def initialize(self):
        logger.info("✅ LeadLagAnalyzer initialized")

    def compute_tlcc(
        self,
        series_a: np.ndarray,
        series_b: np.ndarray,
        max_lag: int = 15
    ) -> tuple[int, float]:
        """
        时滞互相关计算 (Time-Lagged Cross-Correlation)
        找出 B 相对于 A 的领先/滞后偏移量 (正值表示 A 领先 B)
        """
        best_lag = 0
        max_corr = -1.0

        for lag in range(-max_lag, max_lag + 1):
            if lag > 0:
                # A 领先 B (B 滞后 A)
                corr = np.corrcoef(series_a[:-lag], series_b[lag:])[0, 1]
            elif lag < 0:
                # B 领先 A (A 滞后 B)
                lag_abs = abs(lag)
                corr = np.corrcoef(series_a[lag_abs:], series_b[:-lag_abs])[0, 1]
            else:
                corr = np.corrcoef(series_a, series_b)[0, 1]

            if not np.isnan(corr) and corr > max_corr:
                max_corr = corr
                best_lag = lag

        return best_lag, max_corr

    def build_lead_lag_graph(
        self,
        stock_codes: list[str],
        returns_dict: dict[str, np.ndarray],
        max_lag: int = 15,
        corr_threshold: float = 0.5,
        min_lag_threshold: int = 2
    ) -> nx.DiGraph:
        """
        构建 Cluster 内的有向领先图
        """
        G = nx.DiGraph()
        valid_stocks = [s for s in stock_codes if s in returns_dict]

        for i in range(len(valid_stocks)):
            for j in range(i + 1, len(valid_stocks)):
                s_i = valid_stocks[i]
                s_j = valid_stocks[j]

                lag, corr = self.compute_tlcc(returns_dict[s_i], returns_dict[s_j], max_lag=max_lag)

                if corr >= corr_threshold and abs(lag) >= min_lag_threshold:
                    if lag > 0:
                        # i 领先 j -> 边: j -> i (PageRank 入度指向龙头)
                        G.add_edge(s_j, s_i, weight=corr, lag=lag)
                    else:
                        # j 领先 i -> 边: i -> j
                        G.add_edge(s_i, s_j, weight=corr, lag=abs(lag))

        return G

    def identify_leader(self, G: nx.DiGraph) -> list[tuple[str, float]]:
        """
        PageRank 算法排位龙头
        """
        if G.number_of_nodes() == 0:
            return []

        try:
            # 边的方向是 follower -> leader
            pagerank = nx.pagerank(G, alpha=0.85, weight='weight')
            sorted_leaders = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
            return sorted_leaders
        except Exception as e:
            logger.error(f"PageRank computation failed: {e}")
            return []

    def enhance_with_obi_momentum(
        self,
        leaders: list[tuple[str, float]],
        obi_features: dict[str, np.ndarray],
        top_k: int = 3
    ) -> list[tuple[str, float]]:
        """
        OBI 动量增强 (Story 003.03 补充内容)
        在 PageRank 前 K 名中，优先推荐 OBI 变动加速度最正的
        """
        if not leaders or not obi_features:
            return leaders

        candidates = leaders[:top_k]
        enhanced = []

        for code, pr_score in candidates:
            if code in obi_features:
                # 假设 obi_features 是一维时间序列，计算最近 5 分钟的动量 (差分)
                obi_series = obi_features[code]
                momentum = obi_series[-1] - obi_series[-5] if len(obi_series) >= 5 else 0.0

                # 融合分数: PageRank 分数 * (1 + 动量增强因子)
                # 动量通常很小，所以需要一定的缩放
                boost = 1.0 + np.tanh(momentum * 10)
                enhanced.append((code, pr_score * boost))
            else:
                enhanced.append((code, pr_score))

        # 重新排序
        return sorted(enhanced, key=lambda x: x[1], reverse=True)

    def compute_divergence(
        self,
        members: list[str],
        returns_dict: dict[str, np.ndarray],
        window: int = 30
    ) -> np.ndarray:
        """
        计算 Cluster 的分歧度 (Rolling Standard Deviation)
        """
        member_returns = [returns_dict[m] for m in members if m in returns_dict]
        if not member_returns:
            return np.array([])

        df = pd.DataFrame(np.array(member_returns).T)
        divergence = df.std(axis=1)
        return divergence.rolling(window, min_periods=1).mean().values

    def classify_trend_phase(
        self,
        current_divergence: float,
        history_divergence: np.ndarray
    ) -> TrendPhase:
        """
        根据分歧度判定趋势阶段
        """
        if len(history_divergence) < 10:
            return TrendPhase.STEADY

        p20 = np.percentile(history_divergence, 20)
        p80 = np.percentile(history_divergence, 80)

        if current_divergence < p20:
            return TrendPhase.FORMATION
        elif current_divergence > p80:
            return TrendPhase.DISSOLUTION
        else:
            return TrendPhase.STEADY

    async def close(self):
        pass


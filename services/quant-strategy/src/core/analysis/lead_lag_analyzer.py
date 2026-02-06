
import logging
import numpy as np
import pandas as pd
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum

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
    ) -> Tuple[int, float]:
        """
        时滞互相关计算 (Time-Lagged Cross-Correlation)
        找出 B 相对于 A 的领先/滞后偏移量
        """
        best_lag = 0
        max_corr = -1.0
        
        # 简单循环实现，后续可考虑 FFT 加速
        for lag in range(-max_lag, max_lag + 1):
            if lag > 0:
                # A 领先 B (B 滞后 A)
                # A: [0, 1, 2, 3] -> [0, 1, 2]
                # B: [0, 1, 2, 3] -> [1, 2, 3]
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
        stock_codes: List[str], 
        returns_dict: Dict[str, np.ndarray],
        max_lag: int = 15,
        corr_threshold: float = 0.5,
        min_lag_threshold: int = 2
    ) -> nx.DiGraph:
        """
        构建 Cluster 内的有向领先图
        """
        G = nx.DiGraph()
        n = len(stock_codes)
        
        # 预先提取有效序列
        valid_stocks = [s for s in stock_codes if s in returns_dict]
        
        for i in range(len(valid_stocks)):
            for j in range(i + 1, len(valid_stocks)):
                s_i = valid_stocks[i]
                s_j = valid_stocks[j]
                
                lag, corr = self.compute_tlcc(returns_dict[s_i], returns_dict[s_j], max_lag=max_lag)
                
                # 仅保留显著领先关系
                if corr >= corr_threshold and abs(lag) >= min_lag_threshold:
                    if lag > 0:
                        # i 领先 j -> j 跟随 i -> 边: j -> i
                        G.add_edge(s_j, s_i, weight=corr, lag=lag)
                    else:
                        # j 领先 i -> i 跟随 j -> 边: i -> j
                        G.add_edge(s_i, s_j, weight=corr, lag=abs(lag))
                        
        return G

    def identify_leader(self, G: nx.DiGraph) -> List[Tuple[str, float]]:
        """
        PageRank 算法排位龙头
        """
        if G.number_of_nodes() == 0:
            return []
            
        try:
            # 边的方向是 follower -> leader
            # PageRank 权重倾向于入度。在本图中，被跟随越多（入度越高）的节点分数越高，即为龙头。
            pagerank = nx.pagerank(G, alpha=0.85, weight='weight')
            sorted_leaders = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
            return sorted_leaders
        except Exception as e:
            logger.error(f"PageRank computation failed: {e}")
            return []

    def compute_divergence(
        self, 
        members: List[str], 
        returns_dict: Dict[str, np.ndarray],
        window: int = 30
    ) -> np.ndarray:
        """
        计算 Cluster 的分歧度 (Rolling Standard Deviation)
        """
        member_returns = []
        for m in members:
            if m in returns_dict:
                member_returns.append(returns_dict[m])
        
        if not member_returns:
            return np.array([])
            
        # 转换为 DataFrame: (Time, Stocks)
        df = pd.DataFrame(np.array(member_returns).T)
        
        # 计算每一时刻，成员间的标准差
        # axis=1 表示在股票维度计算标准差
        divergence = df.std(axis=1)
        
        # 如果需要滚动平滑
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


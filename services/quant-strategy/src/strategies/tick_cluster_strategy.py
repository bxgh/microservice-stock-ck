import logging
from datetime import datetime

import numpy as np

from analysis.clustering.engine import ClusteringEngine
from analysis.intraday.models import IntradaySignal
from analysis.intraday.momentum_analyzer import IntradayMomentumAnalyzer
from analysis.leadlag.divergence_monitor import TrendPhase
from analysis.leadlag.engine import LeadLagAnalyzer
from analysis.similarity.engine import SimilarityEngine
from models.signal import Signal, SignalType, Priority

logger = logging.getLogger(__name__)


class TickClusterStrategy:
    """
    全市场横截面资金聚类策略的外壳 (Facade)。
    不同于传统的 BaseStrategy（单股串行），该策略每天接收一次全市场的 240 维特征数据，
    交由内置的 3 大微积分引擎联合计算，直接输出第二天的全市场买卖金股名单。
    """

    def __init__(self, strategy_id: str = "TICK_CLUSTER_V1"):
        self.strategy_id = strategy_id

        # 加载三大子引擎
        self.similarity_engine = SimilarityEngine(max_workers=8, dtw_window=15)
        # Default clustering settings with strict noise filter
        self.clustering_engine = ClusteringEngine()
        self.leadlag_analyzer = LeadLagAnalyzer()

        # Intraday Extension
        self.intraday_analyzer = IntradayMomentumAnalyzer()

    def generate_daily_signals(
        self,
        current_date: datetime,
        features_matrix: dict[str, np.ndarray],
        returns_data: dict[str, np.ndarray],
        benchmark_returns: np.ndarray,
        stock_industry: dict[str, str],
        turnover_data: dict[str, float]
    ) -> list[Signal]:
        """
        每日收盘后被回测器或生产调度器拉起，执行全管线推理。

        Args:
            current_date: 分析执行的基准日期
            features_matrix: 9维特征压缩后的目标单维比对序列 (240位)，用于算 DTW
            returns_data: 标准收益率序列 (240位)，用于过滤和测散度
            benchmark_returns: 比如 HS300 收益率，用来过滤纯大盘团伙
            stock_industry: 行业缓存字典，防同质化
            turnover_data: 换手率，防死水股

        Returns:
            List[Signal]: [Signal(stock_A, "BUY"), Signal(stock_B, "BUY")]
        """
        signals = []
        logger.info(f"[{current_date.date()}] Simulating cross-sectional strategy over {len(features_matrix)} stocks.")

        try:
            # 1. 降维粗筛 + DTW 距离计算
            sim_matrix = self.similarity_engine.compute_similarity(features_matrix)

            # 2. 网格重建 + Leiden 社区划分 + 4大防火墙清洗
            fund_clusters = self.clustering_engine.run_clustering(
                sim_matrix,
                stock_returns=returns_data,
                benchmark_returns=benchmark_returns,
                stock_industry=stock_industry,
                turnover_data=turnover_data
            )

            # 3. TLCC 时延 + PageRank 老大挖掘 + 分歧度周期测算
            enhanced_clusters = self.leadlag_analyzer.analyze_clusters(fund_clusters, returns_data)

            # 4. 信号萃取
            # 策略逻辑：只挑选处于“形成期 (FORMATION)”的组织，并且买入指挥整个团伙的大哥
            for cluster in enhanced_clusters:
                if cluster.trend_phase == TrendPhase.FORMATION and cluster.leader_stock != "UNKNOWN":
                    # 强劲的共振信号
                    # 按照 Signal.create() 规范初始化
                    signal = Signal.create(
                        stock_code=cluster.leader_stock,
                        signal_type=SignalType.LONG,
                        priority=Priority.HIGH,
                        price=0.0,
                        score=min(100.0, (cluster.pagerank_score + 0.5) * 100),
                        strategy_name=self.strategy_id,
                        reason=f"Cluster {cluster.cluster_id} formation leader! MemCount: {cluster.member_count}"
                    )
                    signals.append(signal)

            logger.info(f"[{current_date.date()}] Strategy execution complete. Emitted {len(signals)} signals.")

        except Exception as e:
            logger.error(f"[{current_date.date()}] Strategic pipeline failed: {str(e)}", exc_info=True)

        return signals

    def generate_intraday_signals(
        self,
        current_time: datetime,
        yesterday_closes: dict[str, float],
        open_prices: dict[str, float],
        volume_first_30m: dict[str, float],
        volume_avg_20d: dict[str, float],
        intraday_returns: dict[str, float],
        target_pool: list[str],
        cluster_info: dict[str, dict] = None
    ) -> list[IntradaySignal]:
        """
        在日中高频运行或回测环境的模拟高频事件里，根据开盘半小时和昨收，
        寻找 Gap 和跟涨传导机会。

        Args:
            target_pool: 要重点盯盘的股票池（如前日发现的潜在龙头或高活股票）
            cluster_info: 字典 code -> { "cluster_id": id, "role": "LEADER"/"FOLLOWER", "leader_code": str }。盘中传导预测时依赖。

        Returns:
            List[IntradaySignal]: 日内生成的信号列表。
        """
        signals = []
        cluster_info = cluster_info or {}

        logger.info(f"[{current_time}] Running intraday monitoring for {len(target_pool)} stocks.")

        for code in target_pool:
            # 1. 检测跳空回归与突破 (Fade the Gap & Breakaway)
            y_close = yesterday_closes.get(code)
            o_price = open_prices.get(code)
            vol_30m = volume_first_30m.get(code)
            vol_20d = volume_avg_20d.get(code)

            if None not in (y_close, o_price, vol_30m, vol_20d):
                gap_signal = self.intraday_analyzer.analyze_overnight_gap(
                    stock_code=code,
                    current_time=current_time,
                    yesterday_close=y_close,
                    open_price=o_price,
                    volume_first_30m=vol_30m,
                    volume_avg_20d=vol_20d
                )
                if gap_signal:
                    signals.append(gap_signal)

            # 2. 检测群落内部动量传导 (Momentum Lag)
            c_info = cluster_info.get(code)
            if c_info and c_info.get("role") == "FOLLOWER":
                leader_code = c_info.get("leader_code")
                follower_return = intraday_returns.get(code)
                leader_return = intraday_returns.get(leader_code)
                cluster_id = c_info.get("cluster_id")

                if None not in (follower_return, leader_return):
                    lag_signal = self.intraday_analyzer.analyze_momentum_transmission(
                        follower_code=code,
                        current_time=current_time,
                        leader_code=leader_code,
                        leader_intraday_return=leader_return,
                        follower_intraday_return=follower_return,
                        cluster_id=cluster_id
                    )
                    if lag_signal:
                        signals.append(lag_signal)

        logger.info(f"[{current_time}] Intraday scan complete. Emitted {len(signals)} real-time signals.")
        return signals


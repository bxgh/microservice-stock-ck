
"""
LeadLagStrategy 策略类

基于聚类分析和领先-滞后关系的个股联动策略。
"""
import logging
from typing import Any

import pandas as pd
import pytz

from models.signal import Priority, Signal, SignalType
from strategies.base_strategy import BaseStrategy, StrategyResult, Timeframe

logger = logging.getLogger(__name__)

class LeadLagStrategy(BaseStrategy):
    """
    领涨-跟风联动策略

    核心逻辑:
    1. 获取聚类分析结果 (Clusters, Leaders, Divergence)
    2. 当分歧度处于合力期 (Formation) 且存在明确龙头时:
       - 识别跟风股 (Followers)
       - 生成买入信号 (LONG)
    3. 当分歧度进入瓦解期 (Dissolution):
       - 生成卖出信号 (CLOSE)
    """

    def __init__(self, parameters: dict[str, Any] | None = None):
        super().__init__("LeadLagStrategy", parameters)
        self.formation_threshold = self.parameters.get("formation_threshold", 0.3)
        self.dissolution_threshold = self.parameters.get("dissolution_threshold", 0.7)
        self.min_signal_score = self.parameters.get("min_signal_score", 30.0)

    @property
    def strategy_id(self) -> str:
        return "strat_lead_lag_001"

    @property
    def timeframe(self) -> Timeframe:
        return Timeframe.INTRADAY

    async def evaluate(self, stock_code: str, data: dict[str, Any]) -> StrategyResult:
        """
        批量扫描评估 (用于个股层面的评分)
        """
        cluster_info = data.get("cluster_info", {})
        if not cluster_info:
            return StrategyResult(
                strategy_id=self.strategy_id,
                stock_code=stock_code,
                score=0.0,
                passed=False,
                reason="无聚类分析数据"
            )

        divergence = cluster_info.get("divergence", 1.0)
        is_leader = cluster_info.get("is_leader", False)

        # 评分逻辑: 越处于合力期分数越高，龙头分数高于跟随者
        score = (1.0 - divergence) * 100.0
        if is_leader:
            score += 10.0 # 龙头溢价

        score = min(max(score, 0.0), 100.0)

        return StrategyResult(
            strategy_id=self.strategy_id,
            stock_code=stock_code,
            score=score,
            passed=score >= 60.0,
            reason=f"分歧度 {divergence:.2f}" + (" (龙头)" if is_leader else ""),
            details=cluster_info
        )

    async def generate_signals_from_analysis(
        self,
        trade_date: str,
        clusters_df: pd.DataFrame
    ) -> list[Signal]:
        """
        从分析服务生成的聚类 DataFrame 批量生成信号

        Args:
            trade_date: 交易日期
            clusters_df: 包含 cluster_id, members, leaders, divergence, trend_phase 的 DataFrame

        Returns:
            Signal 列表
        """
        logger.info(f"🚀 Generating signals for {trade_date} with {len(clusters_df)} clusters")
        signals = []
        pytz.timezone('Asia/Shanghai')

        for _, row in clusters_df.iterrows():
            cluster_id = row['cluster_id']
            members = row['members']
            leaders = row['leaders'] # 格式可能为 [('code', score), ...] 或 ['code', ...]
            divergence = row.get('current_divergence', row.get('divergence', 0.5))
            trend_phase = row.get('trend_phase', 'neutral')

            if not leaders or not members:
                continue

            # 提取龙头代码
            leader_code = leaders[0][0] if isinstance(leaders[0], tuple) else leaders[0]

            # --- 信号生成策略 ---

            # 1. 合力期 (Formation) -> 买入跟风者
            if trend_phase in ['formation', '合力形成期'] or divergence < self.formation_threshold:
                followers = [m for m in members if m != leader_code]
                for fol in followers:
                    score = (1.0 - divergence) * 100.0
                    if score < self.min_signal_score:
                        continue

                    signals.append(Signal.create(
                        stock_code=fol,
                        signal_type=SignalType.LONG,
                        priority=Priority.MEDIUM,
                        strategy_name=self.name,
                        reason=f"群组{cluster_id}共振强(div={divergence:.2f})，跟随龙头{leader_code} ({trend_phase})",
                        score=score,
                        metadata={
                            "cluster_id": cluster_id,
                            "leader": leader_code,
                            "divergence": divergence,
                            "phase": trend_phase,
                            "trade_date": trade_date
                        }
                    ))

            # 2. 瓦解期 (Dissolution) -> 全员卖出/减仓
            elif trend_phase in ['dissolution', '瓦解期'] or divergence > self.dissolution_threshold:
                for member_code in members:
                    signals.append(Signal.create(
                        stock_code=member_code,
                        signal_type=SignalType.CLOSE,
                        priority=Priority.HIGH,
                        strategy_name=self.name,
                        reason=f"群组{cluster_id}瓦解(div={divergence:.2f})，回避分歧 ({trend_phase})",
                        score=divergence * 100.0,
                        metadata={
                            "cluster_id": cluster_id,
                            "divergence": divergence,
                            "phase": trend_phase,
                            "trade_date": trade_date
                        }
                    ))

        logger.info(f"✅ Generated {len(signals)} signals for {trade_date}")
        return signals

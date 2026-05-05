import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from src.strategies.geopolitical.constants import ScenarioType

logger = logging.getLogger(__name__)

class GeopoliticalScoringEngine:
    """
    地缘冲突评分引擎
    根据 IranWar_v2.md 定义的权重矩阵进行多维度评分融合。
    """

    def __init__(self):
        # 权重定义 (严格遵循 IranWar_v2.md)
        self.weights = {
            "excess_return": 0.30,  # 抗跌能力
            "max_drawdown": 0.20,   # 回撤控制
            "bonus": 0.20,          # 题材/防御板块加成
            "volume_ratio": 0.10,   # 流动性 (缩量为佳)
            "base_alpha": 0.20      # 基础 Alpha (基本面+估值)
        }

    def _normalize_excess_return(self, val: float) -> float:
        """归一化超额收益: -20% -> 0, 0% -> 50, +20% -> 100"""
        return np.clip((val + 0.20) / 0.40 * 100, 0, 100)

    def _normalize_drawdown(self, val: float) -> float:
        """归一化最大回撤: -20% -> 0, -10% -> 50, 0% -> 100"""
        return np.clip((val + 0.20) / 0.20 * 100, 0, 100)

    def _normalize_volume_ratio(self, val: float) -> float:
        """归一化缩量比: 2.0 (放量) -> 0, 1.0 -> 50, 0.5 (大幅缩量) -> 100"""
        # 注意：缩量是防御性强的表现，所以值越小分越高
        if val <= 0: return 0
        return np.clip((2.0 - val) / 1.5 * 100, 0, 100)

    def score_defense(
        self, 
        base_factors_df: pd.DataFrame, 
        bonuses: Dict[str, Tuple[float, str]],
        scenario: ScenarioType
    ) -> pd.DataFrame:
        """
        综合评分核心逻辑
        
        Args:
            base_factors_df: 包含 code, excess_return, max_drawdown, volume_ratio, score (base_alpha)
            bonuses: {code: (bonus_value, reason)}
            scenario: 当前场景
            
        Returns:
            pd.DataFrame: 包含 code, final_score, 和各维度得分
        """
        if base_factors_df.empty:
            return pd.DataFrame()

        df = base_factors_df.copy()

        # 1. 维度得分计算
        df['s_excess'] = df['excess_return'].apply(self._normalize_excess_return)
        df['s_drawdown'] = df['max_drawdown'].apply(self._normalize_drawdown)
        df['s_volume'] = df['volume_ratio'].apply(self._normalize_volume_ratio)
        
        # 2. 题材加分处理
        # bonuses 里的 bonus_value 已经是 0-15 之间的加分，此处映射到 0-100 分度
        # 假设最高加分 15 分对应 题材维度 100 分
        df['s_bonus'] = df['code'].apply(lambda x: min(100, (bonuses.get(x, (0, ""))[0] / 15.0) * 100))

        # 3. 基础 Alpha 得分 (假设已经是 0-100)
        df['s_base'] = df.get('score', 60.0) # 默认 60 分

        # 4. 加权汇总
        df['final_score'] = (
            df['s_excess'] * self.weights['excess_return'] +
            df['s_drawdown'] * self.weights['max_drawdown'] +
            df['s_bonus'] * self.weights['bonus'] +
            df['s_volume'] * self.weights['volume_ratio'] +
            df['s_base'] * self.weights['base_alpha']
        )

        # 5. 排序
        df = df.sort_values('final_score', ascending=False)
        
        logger.info(f"Scoring completed for {len(df)} stocks. Top score: {df['final_score'].max():.2f}")
        return df

# 单例
geopolitical_scoring_engine = GeopoliticalScoringEngine()

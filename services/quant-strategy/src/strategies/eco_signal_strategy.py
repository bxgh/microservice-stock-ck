import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class EcoSignalStrategy(BaseStrategy):
    """
    AI 产业链另类数据策略 — 生态特征信号与 Z-Score 信号提纯策略。
    使用 numpy/pandas 纯向量运算实现针对时间序列的 0 loop 处理。
    """

    def __init__(self, window_size: int = 30):
        super().__init__(name="EcoSignalStrategy")
        # Rolling window 用作 Z-score 从均值向极值的偏离基准
        self.window_size = window_size
        
    @property
    def strategy_id(self) -> str:
        return "ECO_SIGNAL_01"
        
    async def evaluate(self, stock_code: str, data: dict) -> any:
        """
        单股评估接口。
        注意：本策略主供 ClickHouse 数据清洗及入库使用，选股时由 StockSelector 进行二次调用，
        此接口仅提供基类实现防止报错。
        """
        from src.strategies.base_strategy import StrategyResult
        return StrategyResult(
            strategy_id=self.strategy_id,
            stock_code=stock_code,
            score=50.0,
            passed=False,
            reason="Not applicable for single stock raw evaluation"
        )

    def calculate_signals(self, raw_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        通过输入 N 个维度的时序特征记录，针对某个独立 Label 的群体，将其凝聚到大盘级别的特征评级信号中。
        输入时应该是单一 Label 按 collect_time 排序的 df。
        """
        if raw_df is None or raw_df.empty:
            logger.warning("Empty raw_df provided to EcoSignalStrategy")
            return None

        df = raw_df.copy()

        # 1. 计算三项聚类复合特征
        # Momentum = pr_merged_acceleration (已提取) + 本周的所有提交数
        df["eco_momentum"] = df["pr_merged_acceleration"] + df["commit_count_7d"]

        # Responsiveness: issue 响应极值。由于数值越低响应越快代表活性越强，使用负倒数进行同质化：耗时越小值越大
        # 为避免除以 0 以及平滑数据，采用 24 / (x + 1) -> 即 1 天为基准的活跃比
        df["eco_responsiveness"] = 24.0 / (df["issue_close_median_hours"] + 1.0)

        # Growth: 涨幅与受众参与
        df["eco_growth"] = df["star_delta_7d"] + df["contributor_count_30d"]

        # 2. 跨度由于这三个量纲绝对不同 (Commit 数可能数千，而 Responsiveness 一般在 1~24)。
        # 因此，进行分别滚动独立 Z-Score 映射后再汇总均值更加平滑。
        for col in ["eco_momentum", "eco_responsiveness", "eco_growth"]:
            z_col = f"z_{col}"
            rolling = df[col].rolling(window=self.window_size, min_periods=3)
            mean = rolling.mean()
            std = rolling.std()
            
            # 使用 numpy where 安全处理标准差等于0的情况 (除以0得到NaN)
            df[z_col] = np.where(std > 0, (df[col] - mean) / std, 0.0)

        # 3. 产生最终复合判断基准与最突出的特征成分
        df["composite_z_score"] = df[["z_eco_momentum", "z_eco_responsiveness", "z_eco_growth"]].mean(axis=1)

        # 找出引发近期爆发最主要的单一主力：
        def _get_dominant(row):
            scores = {
                "MOMENTUM": row["z_eco_momentum"],
                "RESPONSIVENESS": row["z_eco_responsiveness"],
                "GROWTH": row["z_eco_growth"]
            }
            # 如果复合不足以称为“上升因素”，主力因子退化为 NONE
            if row["composite_z_score"] < 1.0:
                return "NONE"
            return max(scores, key=scores.get)

        df["dominant_factor"] = df.apply(_get_dominant, axis=1)

        # 4. 基于整体平均后的 Z-Score 做景气度离散划线 (NEUTRAL/WARM/HOT/EXTREME)
        conditions = [
            (df["composite_z_score"] >= 3.0),
            (df["composite_z_score"] >= 2.0) & (df["composite_z_score"] < 3.0),
            (df["composite_z_score"] >= 1.0) & (df["composite_z_score"] < 2.0),
            (df["composite_z_score"] < 1.0)
        ]
        choices = ["EXTREME", "HOT", "WARM", "NEUTRAL"]
        
        df["signal_level"] = np.select(conditions, choices, default="NEUTRAL")

        # 5. 生成结果记录。一般我们只返回最后一条供当前决策或入库，但为了支持量化回测阶段(Story 17.7)：
        # 返回被补全并重命名为标准写入格式的整张全时序表。
        result_df = pd.DataFrame()
        result_df["signal_time"] = df["collect_time"]
        result_df["label"] = df["label"]
        result_df["composite_z_score"] = df["composite_z_score"].fillna(0.0).round(4)
        result_df["dominant_factor"] = df["dominant_factor"]
        result_df["signal_level"] = df["signal_level"]
        
        # 记录其成分值供可视化或报告引用
        df["detail"] = (
            "M:" + df["z_eco_momentum"].round(2).astype(str) + 
            "|R:" + df["z_eco_responsiveness"].round(2).astype(str) + 
            "|G:" + df["z_eco_growth"].round(2).astype(str)
        )
        result_df["detail"] = df["detail"]

        return result_df

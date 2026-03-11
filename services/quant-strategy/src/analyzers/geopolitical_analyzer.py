import numpy as np
import pandas as pd
from typing import Dict, Any

class GeopoliticalAnalyzer:
    """
    地缘冲突特征分析器
    用于量化计算个股在特定“暴跌区间”或“冲突期间”的抗跌性及流动性指标。
    """

    @staticmethod
    def calculate_excess_return(stock_df: pd.DataFrame, index_df: pd.DataFrame) -> float:
        """
        计算区间超额收益率 (Excess Return)
        指标定义：个股涨跌幅 - 基准指数涨跌幅
        """
        if stock_df.empty or index_df.empty:
            return 0.0

        # 确保按日期排序
        stock_df = stock_df.sort_values('trade_date')
        index_df = index_df.sort_values('trade_date')

        # 计算个股跌幅
        s_base = stock_df.iloc[0]['close']
        s_curr = stock_df.iloc[-1]['close']
        s_change = (s_curr - s_base) / s_base

        # 计算基准跌幅
        i_base = index_df.iloc[0]['close']
        i_curr = index_df.iloc[-1]['close']
        i_change = (i_curr - i_base) / i_base

        return s_change - i_change

    @staticmethod
    def calculate_max_drawdown(stock_df: pd.DataFrame) -> float:
        """
        计算区间最大回撤 (Max Drawdown)
        """
        if stock_df.empty:
            return 0.0

        # 确保按日期排序
        prices = stock_df.sort_values('trade_date')['close'].values
        
        # 向量化计算回撤
        peak = np.maximum.accumulate(prices)
        drawdown = (prices - peak) / peak
        return np.min(drawdown)

    @staticmethod
    def calculate_volume_ratio(stock_df: pd.DataFrame, pre_war_avg_vol: float) -> float:
        """
        计算缩量比 (Volume Ratio)
        指标定义：区间日均成交量 / 战前20日日均成交量
        缩量通常代表持有者惜售，防御性更强。
        """
        if stock_df.empty or pre_war_avg_vol <= 0:
            return 1.0
            
        curr_avg_vol = stock_df['volume'].mean()
        return curr_avg_vol / pre_war_avg_vol

    def compute_all_metrics(
        self, 
        stock_df: pd.DataFrame, 
        index_df: pd.DataFrame, 
        pre_war_vol: float
    ) -> Dict[str, float]:
        """
        一次性计算所有防御性指标
        """
        return {
            "excess_return": self.calculate_excess_return(stock_df, index_df),
            "max_drawdown": self.calculate_max_drawdown(stock_df),
            "volume_ratio": self.calculate_volume_ratio(stock_df, pre_war_vol)
        }

"""绩效分析器

本模块负责根据净值曲线计算核心绩效指标。
包括收益率、回撤、夏普比率等计算逻辑。
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

from .models import PerformanceMetrics, TradeRecord

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """绩效分析器"""
    
    @staticmethod
    def calculate(
        equity_curve: List[Dict[str, Any]],
        trades: List[TradeRecord],
        risk_free_rate: float = 0.03
    ) -> PerformanceMetrics:
        """
        计算绩效指标
        
        Args:
            equity_curve: 净值曲线列表 [{'date': datetime, 'value': float}]
            trades: 交易记录列表
            risk_free_rate: 年化无风险利率
            
        Returns:
            PerformanceMetrics对象
        """
        if not equity_curve:
            return PerformanceAnalyzer._create_empty_metrics()
            
        # 转换为DataFrame处理
        df = pd.DataFrame(equity_curve)
        df.set_index('date', inplace=True)
        df['value'] = df['value'].astype(float)
        
        # 计算日收益率
        df['returns'] = df['value'].pct_change().fillna(0)
        
        # 1. 基础收益指标
        initial_value = df['value'].iloc[0]
        final_value = df['value'].iloc[-1]
        
        total_return = (final_value / initial_value) - 1
        
        # 年化收益率
        days = (df.index[-1] - df.index[0]).days
        if days > 0:
            annualized_return = (1 + total_return) ** (365 / days) - 1
        else:
            annualized_return = 0.0
            
        # 2. 风险指标
        max_drawdown = PerformanceAnalyzer._calculate_max_drawdown(df['value'])
        volatility = df['returns'].std() * np.sqrt(252) # 年化波动率
        sharpe_ratio = PerformanceAnalyzer._calculate_sharpe_ratio(
            df['returns'], risk_free_rate
        )
        
        # 3. 交易统计
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if PerformanceAnalyzer._is_winning_trade(t))
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        return PerformanceMetrics(
            total_return=round(total_return, 4),
            annualized_return=round(annualized_return, 4),
            max_drawdown=round(max_drawdown, 4),
            sharpe_ratio=round(sharpe_ratio, 4),
            volatility=round(volatility, 4),
            win_rate=round(win_rate, 4),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
    
    @staticmethod
    def _calculate_max_drawdown(equity_series: pd.Series) -> float:
        """计算最大回撤"""
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        return abs(drawdown.min())
    
    @staticmethod
    def _calculate_sharpe_ratio(returns_series: pd.Series, risk_free_rate: float) -> float:
        """计算年化夏普比率"""
        if returns_series.std() == 0:
            return 0.0
            
        # 转换无风险利率为日频
        daily_rf = (1 + risk_free_rate) ** (1/252) - 1
        
        excess_returns = returns_series - daily_rf
        mean_excess_return = excess_returns.mean()
        std_dev = returns_series.std()
        
        # 年化
        sharpe = (mean_excess_return / std_dev) * np.sqrt(252)
        return float(sharpe)
    
    @staticmethod
    def _is_winning_trade(trade: TradeRecord) -> bool:
         # 这是一个简化的判断，实际应该看平仓时的盈亏
         # 这里因为TradeRecord是单笔成交，无法直接看出盈亏
         # 需要由Engine在生成TradeRecord时计算盈亏，或者传入Pairs
         # 暂时简化：假设如果是有收益的卖出就算赢（需要配合Engine逻辑）
         # TODO: 完善TradeRecord结构以包含每笔交易的P&L
         return True # Placeholder
         
    @staticmethod
    def _create_empty_metrics() -> PerformanceMetrics:
        return PerformanceMetrics(
            total_return=0.0, annualized_return=0.0, max_drawdown=0.0,
            sharpe_ratio=0.0, volatility=0.0, win_rate=0.0,
            total_trades=0, winning_trades=0, losing_trades=0
        )

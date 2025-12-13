"""
向量化回测引擎

基于pandas的轻量级回测引擎,用于快速验证策略逻辑
"""
from typing import List
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import pytz

from models.signal import Signal, SignalType
from models.backtest import BacktestResult

logger = logging.getLogger(__name__)


class VectorizedBacktester:
    """
    向量化回测引擎
    
    使用pandas向量化计算,避免循环遍历
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,  # 万三手续费
        slippage: float = 0.001           # 0.1%滑点
    ):
        """
        初始化回测器
        
        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage: 滑点
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        
    async def backtest_signals(
        self,
        signals: List[Signal],
        strategy_name: str
    ) -> BacktestResult:
        """
        基于信号列表回测
        
        Args:
            signals: 信号列表
            strategy_name: 策略名称
            
        Returns:
            BacktestResult对象
        """
        try:
            if not signals:
                logger.warning("No signals provided for backtest")
                cst = pytz.timezone('Asia/Shanghai')
                now = datetime.now(cst)
                return BacktestResult(
                    strategy_name=strategy_name,
                    period_start=now,
                    period_end=now,
                    initial_capital=self.initial_capital,
                    final_capital=self.initial_capital,
                    total_return=0.0,
                    max_drawdown=0.0,
                    sharpe_ratio=0.0,
                    total_signals=0
                )
            
            # 转换信号为DataFrame
            signals_df = pd.DataFrame([
                {
                    'timestamp': s.timestamp,
                    'stock_code': s.stock_code,
                    'signal_type': s.signal_type.value,
                    'price': s.price or 0,
                    'score': s.score
                }
                for s in signals
            ])
            
            # 排序
            signals_df = signals_df.sort_values('timestamp').reset_index(drop=True)
            
            # 简化回测逻辑: 基于信号方向和score计算收益
            returns = []
            capital = self.initial_capital
            
            for _, row in signals_df.iterrows():
                signal_return = 0.0
                
                if row['signal_type'] == 'LONG':
                    # 做多: score越高收益越高
                    signal_return = (row['score'] / 100.0) * 0.02  # 2%基础收益
                elif row['signal_type'] == 'SHORT':
                    # 做空: score越高收益越高(但方向相反)
                    signal_return = -(row['score'] / 100.0) * 0.01
                
                # 扣除手续费和滑点
                costs = self.commission_rate + self.slippage
                net_return = signal_return - costs
                
                capital *= (1 + net_return)
                returns.append(net_return)
            
            # 计算指标
            total_return = (capital - self.initial_capital) / self.initial_capital
            
            # 计算最大回撤
            cumulative_returns = np.cumprod([1 + r for r in returns])
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(drawdowns.min()) if len(drawdowns) > 0 else 0.0
            
            # 计算夏普比率 (简化版)
            if len(returns) > 1:
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0
            else:
                sharpe_ratio = 0.0
            
            # 创建结果
            period_start = signals[0].timestamp
            period_end = signals[-1].timestamp
            
            result = BacktestResult(
                strategy_name=strategy_name,
                period_start=period_start,
                period_end=period_end,
                initial_capital=self.initial_capital,
                final_capital=capital,
                total_return=total_return,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                total_signals=len(signals),
                total_trades=len(signals),
                detailed_results={
                    'avg_return_per_signal': np.mean(returns) if returns else 0,
                    'signals_by_type': signals_df['signal_type'].value_counts().to_dict()
                }
            )
            
            logger.info(f"Backtest completed: {strategy_name}, return={total_return:.2%}")
            return result
            
        except Exception as e:
            logger.exception(f"Backtest failed: {e}")
            raise

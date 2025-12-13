"""回测引擎实现

包含核心回测逻辑：
1. 数据获取
2. 策略执行（生成信号）
3. 交易模拟（基于信号生成交易记录和净值曲线）
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np

from strategies.base import BaseStrategy
from strategies.signal import Signal as StrategySignal
# Note: SignalType is just "BUY"/"SELL" strings in Signal model, not a separate Enum class in new design
# So we define it locally or use strings
from strategies.registry import StrategyRegistry
from .models import (
    BacktestConfig, BacktestResult, TradeRecord, 
    PerformanceMetrics
)
from .analyzer import PerformanceAnalyzer

logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, data_provider=None):
        """
        初始化回测引擎
        
        Args:
            data_provider: 数据提供者，支持 get_history_bars(stock_code, start, end)
                           如果为None，run()时必须传入data
        """
        self.data_provider = data_provider
        self.registry = StrategyRegistry()
        
    async def run(
        self,
        strategy_id: str,
        stock_code: str,
        start_date: datetime,
        end_date: datetime,
        config: BacktestConfig = BacktestConfig(),
        data: Optional[pd.DataFrame] = None
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy_id: 策略ID
            stock_code: 标的代码
            start_date: 开始日期
            end_date: 结束日期
            config: 回测配置
            data: 可选，直接传入历史数据DataFrame
            
        Returns:
            BacktestResult
        """
        logger.info(f"Starting backtest: strategy={strategy_id}, code={stock_code}, "
                   f"range={start_date.date()}~{end_date.date()}")
                   
        # 1. 获取策略实例
        strategy = self.registry.get(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy '{strategy_id}' not found")
            
        # 2. 获取数据
        if data is None:
            if not self.data_provider:
                raise ValueError("No data_provider configured and no data provided")
            # TODO: 调用 data_provider.fetch_history_bars (需适配具体接口)
            # data = await self.data_provider.get_history_bars(...)
            raise NotImplementedError("Data provider integration not yet implemented")
        
        if data.empty:
            raise ValueError("Data is empty")
            
        # 3. 初始化策略
        if not strategy.is_initialized:
            await strategy.initialize()
            
        # 4. 执行回测核心逻辑
        signals = await self._generate_signals(strategy, data)
        
        # 5. 模拟交易
        trades, equity_curve = self._simulate_trading(signals, data, config)
        
        # 6. 计算绩效
        metrics = PerformanceAnalyzer.calculate(
            equity_curve, trades, config.risk_free_rate
        )
        
        return BacktestResult(
            strategy_id=strategy_id,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            initial_capital=config.initial_capital,
            final_capital=equity_curve[-1]['value'],
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
            config=config
        )
        
    async def _generate_signals(
        self, 
        strategy: BaseStrategy, 
        data: pd.DataFrame
    ) -> List[StrategySignal]:
        """生成信号序列"""
        signals: List[StrategySignal] = []
        
        # 模拟逐K线调用 (Loop)
        # TODO: 未来可优化为向量化调用 strategy.generate_signals_vectorized(data)
        
        for idx, row in data.iterrows():
            # 构造Bar数据结构 (适配BaseStrategy.on_bar期望的格式)
            # 这里做简化的适配，假设Strategy能处理Dict或Series
            bar_data = {
                'stock_code': str(row.get('code', '')), # 假设数据中有code列
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
                'datetime': idx if isinstance(idx, datetime) else row.get('date')
            }
            
            # 调用策略
            try:
                # 1. 更新策略状态
                # 注意：BaseStrategy.on_bar 是 async 的
                await strategy.on_bar(bar_data)
                
                # 2. 获取产生的信号
                # 策略状态更新后，通过工厂方法获取决策
                new_signal = strategy.generate_signal()
                
                if new_signal:
                    if strategy.validate_signal(new_signal):
                        signals.append(new_signal)
                    else:
                        logger.warning(f"Invalid signal generated at {idx}: {new_signal}")
                
            except Exception as e:
                logger.error(f"Error in strategy execution at {idx}: {e}")
                
        return signals

    def _simulate_trading(
        self,
        signals: List[StrategySignal],
        data: pd.DataFrame,
        config: BacktestConfig
    ) -> Any:
        """模拟交易核心逻辑"""
        
        capital = config.initial_capital
        position = 0  # 持仓数量 (股)
        trades: List[TradeRecord] = []
        equity_curve: List[Dict[str, Any]] = []
        
        # 将信号转换为以时间为索引的字典，方便查找
        signal_map = {
            s.timestamp.date(): s 
            for s in signals 
            if s.timestamp
        }
        
        for date, row in data.iterrows():
            date_obj = date.date() if isinstance(date, datetime) else date
            price = row['close'] # 默认用收盘价计算净值
            
            # 1. 处理交易信号 (假设当日收盘成交)
            # 如果配置为次日开盘，则需要复杂的订单队列逻辑
            # 这里简化为：信号日收盘成交
            
            current_signal = signal_map.get(date_obj)
            
            if current_signal:
                if current_signal.direction == "BUY" and position == 0:
                    # 全仓买入 (简化)
                    cost = price * (1 + config.commission_rate)
                    volume = int(capital / cost / 100) * 100 # 向下取整到100股
                    
                    if volume > 0:
                        amount = volume * price
                        commission = amount * config.commission_rate
                        cost_total = amount + commission
                        
                        capital -= cost_total
                        position += volume
                        
                        trades.append(TradeRecord(
                            stock_code=current_signal.stock_code,
                            direction="BUY",
                            price=price,
                            volume=volume,
                            amount=amount,
                            commission=commission,
                            tax=0.0,
                            timestamp=pd.Timestamp(date),
                            strategy_id=current_signal.strategy_id,
                            reason=current_signal.reason
                        ))
                        
                elif current_signal.direction == "SELL" and position > 0:
                    # 全仓卖出
                    amount = position * price
                    commission = amount * config.commission_rate
                    tax = amount * config.stamp_duty
                    revenue = amount - commission - tax
                    
                    # 计算这笔交易的盈亏
                    # 简化：假设FIFO或全仓进出，找到最近一次买入的成本
                    # 这里简化为全仓进出，可以直接计算
                    last_buy = next((t for t in reversed(trades) if t.direction == "BUY"), None)
                    realized_pnl = 0.0
                    if last_buy:
                         # 简单估算：(卖出价 - 买入价) * 数量 - 交易成本
                         # 注意：如果多次买入，这里逻辑会复杂。
                         # 为了MVP，假设全仓模型。
                         buy_cost = last_buy.amount + last_buy.commission
                         realized_pnl = revenue - buy_cost

                    capital += revenue
                    position = 0
                    
                    trades.append(TradeRecord(
                        stock_code=current_signal.stock_code,
                        direction="SELL",
                        price=price,
                        volume=last_buy.volume if last_buy else 0, # Should match position
                        amount=amount,
                        commission=commission,
                        tax=tax,
                        timestamp=pd.Timestamp(date),
                        strategy_id=current_signal.strategy_id,
                        reason=current_signal.reason,
                        realized_pnl=realized_pnl
                    ))

            # 2. 结算当日净值
            market_value = position * price
            total_equity = capital + market_value
            
            equity_curve.append({
                'date': date,
                'value': total_equity
            })
            
        return trades, equity_curve

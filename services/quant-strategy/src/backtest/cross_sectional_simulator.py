import logging
from datetime import datetime
from typing import Any

import pandas as pd
from models.signal import Signal

from backtest.analyzer import PerformanceAnalyzer
from backtest.models import BacktestResult, TradeRecord
from strategies.tick_cluster_strategy import TickClusterStrategy

logger = logging.getLogger(__name__)

class VirtualPortfolio:
    """简单的多头隔日平仓电子账簿，用于横截面模拟验证"""

    def __init__(self, initial_capital: float = 1_000_000.0, commission: float = 0.0003, stamp_duty: float = 0.001):
        self.initial_capital = initial_capital
        self.cash = initial_capital

        # 记录每只股票持仓的数量与其建仓成本价：{stock_code: (volume, entry_price)}
        self.positions: dict[str, tuple[int, float]] = {}

        self.commission = commission
        self.stamp_duty = stamp_duty
        self.trade_history: list[TradeRecord] = []
        self.equity_curve: list[dict[str, Any]] = []

    def close_all_positions(self, current_date: datetime, prices: dict[str, float]) -> None:
        """多头策略的 T+1 止盈出局。无情抛售之前所有的仓位"""
        to_sell = list(self.positions.keys())
        for code in to_sell:
            vol, entry_price = self.positions[code]
            close_price = prices.get(code, entry_price) # 如果因为退市停牌拿不到价格，按成本结走

            amount = vol * close_price
            comm_fee = amount * self.commission
            tax_fee = amount * self.stamp_duty

            revenue = amount - comm_fee - tax_fee
            self.cash += revenue

            pnl = revenue - (vol * entry_price * (1 + self.commission))

            self.trade_history.append(
                TradeRecord(
                    stock_code=code,
                    direction="SELL",
                    price=close_price,
                    volume=vol,
                    amount=amount,
                    commission=comm_fee,
                    tax=tax_fee,
                    timestamp=pd.Timestamp(current_date),
                    strategy_id="BACKTEST_SINK",
                    reason="T+1 Auto Close",
                    realized_pnl=pnl
                )
            )
            del self.positions[code]

    def open_positions(self, current_date: datetime, signals: list[Signal], prices: dict[str, float], max_weight: float = 0.1):
        """根据传入的开仓买入队列平分目前的资金额度"""
        if not signals:
            return

        # 安全资金 (留 5% 缓冲区避免零星差额透支)
        available_cash = self.cash * 0.95
        if available_cash <= 0:
            return

        # 分配买入额度
        slots = len(signals)
        ideal_alloc = available_cash / slots
        max_capital_per_stock = self.initial_capital * max_weight

        actual_alloc = min(ideal_alloc, max_capital_per_stock)

        for sig in signals:
            code = sig.stock_code
            buy_price = prices.get(code)

            # 如果没有取到次日的开盘/收盘价，或价格为0，跳过买入
            if buy_price is None or buy_price <= 0.01:
                logger.warning(f"[{current_date.date()}] Failed to buy {code}, missing simulation price.")
                continue

            # 计算可买整数手
            volume = int(actual_alloc / buy_price / 100) * 100
            if volume <= 0:
                continue

            amount = volume * buy_price
            comm_fee = amount * self.commission
            cost = amount + comm_fee

            self.cash -= cost
            self.positions[code] = (volume, buy_price)

            self.trade_history.append(
                TradeRecord(
                    stock_code=code,
                    direction="BUY",
                    price=buy_price,
                    volume=volume,
                    amount=amount,
                    commission=comm_fee,
                    tax=0.0,
                    timestamp=pd.Timestamp(current_date),
                    strategy_id=sig.strategy_name,
                    reason=sig.reason
                )
            )

    def mark_to_market(self, current_date: datetime, prices: dict[str, float]):
        """根据收市价记账"""
        position_value = 0.0
        for code, (vol, entry_p) in self.positions.items():
            market_price = prices.get(code, entry_p)
            position_value += vol * market_price

        total_equity = self.cash + position_value
        self.equity_curve.append({
            'date': pd.Timestamp(current_date),
            'value': total_equity
        })


class CrossSectionalSimulator:
    """横截面并行回测器"""

    def __init__(self, data_provider=None):
        """
        必须挂载一个 DataProvider, 它应当具备接口:
          - get_trading_dates(start, end)
          - get_cross_sectional_features(date)  -> 传给策略脑的特征
          - get_cross_sectional_prices(date)    -> 仿真器结算用的买卖价格
        """
        self.provider = data_provider

    async def run_simulation(
        self,
        strategy: TickClusterStrategy,
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:

        logger.info(f"Cross-Sectional Vector Backtest started for range {start_date.date()} to {end_date.date()}")

        # 为了单元测试的注入方便，容许无 provider 时抛出 NotImplemented
        if self.provider is None:
            raise NotImplementedError("CrossSectionalSimulator requires a valid data provider.")

        dates = await self.provider.get_trading_dates(start_date, end_date)
        portfolio = VirtualPortfolio()

        pending_buy_signals = []

        for _i, current_date in enumerate(dates):

            # 第一阶段: 结算昨日安排下来的任务 (我们在今天成交)
            # 加载今天市场上的开盘价或收盘价用以计算
            today_prices = await self.provider.get_cross_sectional_prices(current_date)

            # 策略：简单的 T+1，只要有任何持仓今天全部出清，空出资金来响应 pending_buy_signals
            portfolio.close_all_positions(current_date, today_prices)

            # 动用腾出的资产按照买入阵列建仓
            portfolio.open_positions(current_date, pending_buy_signals, today_prices)

            # 第二阶段: 调用核心大脑计算今天的特征，准备明天的操作池
            features_matrix, returns_data, bm_returns, industry_map, turnover = await self.provider.get_cross_sectional_features(current_date)

            if features_matrix:
                pending_buy_signals = strategy.generate_daily_signals(
                    current_date=current_date,
                    features_matrix=features_matrix,
                    returns_data=returns_data,
                    benchmark_returns=bm_returns,
                    stock_industry=industry_map,
                    turnover_data=turnover
                )
            else:
                pending_buy_signals = []

            # 第三阶段: 日终盘点
            portfolio.mark_to_market(current_date, today_prices)

        # 流程结束，收尾统计
        metrics = PerformanceAnalyzer.calculate(
            portfolio.equity_curve,
            portfolio.trade_history,
            risk_free_rate=0.03
        )

        return BacktestResult(
            strategy_id=strategy.strategy_id,
            stock_code="CROSS_MARKET",
            start_date=start_date,
            end_date=end_date,
            initial_capital=portfolio.initial_capital,
            final_capital=portfolio.equity_curve[-1]['value'] if portfolio.equity_curve else portfolio.initial_capital,
            metrics=metrics,
            equity_curve=portfolio.equity_curve,
            trades=portfolio.trade_history,
            config=None
        )

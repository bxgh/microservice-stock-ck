"""Backtest Engine Tests"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from backtest.engine import BacktestEngine
from backtest.models import BacktestConfig
from strategies.base import BaseStrategy
from strategies.signal import Signal as StrategySignal


class MockStrategy(BaseStrategy):
    async def _do_initialize(self):
        self.signal_count = 0

    async def on_bar(self, bar_data: dict):
        # 简单的Mock策略：每隔一天买入，再隔一天卖出
        date = bar_data['datetime']
        # 假设date是index, 可能是timestamp
        if isinstance(date, pd.Timestamp) or isinstance(date, datetime):
            # day = date.day
            pass
        else:
            # day = 1 # Mock
            pass

        self.signal_count += 1
        return None # on_bar不返回信号，而是通过内部状态产生？
        # BacktestEngine _generate_signals 目前是个TODO
        # 我们需要在测试中Hack一下 BacktestEngine._generate_signals
        # 或者让MockStrategy真正的配合 _generate_signals

    # 我们为了测试 BacktestEngine._simulate_trading，
    # 其实可以直接测试 _simulate_trading 方法，传入伪造的信号列表。
    # 这样可以解耦 _generate_signals 的实现不确定性。

class TestBacktestEngine:

    @pytest.mark.asyncio
    async def test_simulate_trading(self):
        """测试交易模拟逻辑"""
        engine = BacktestEngine(data_provider=None)

        # 1. 构造数据 100, 105, 110, 100
        dates = pd.date_range(start='2025-01-01', periods=4)
        data = pd.DataFrame({
            'close': [100.0, 105.0, 110.0, 100.0],
            'open': [100, 104, 109, 99],
            'high': [100, 105, 110, 100],
            'low': [100, 105, 110, 100],
            'volume': [1000, 1000, 1000, 1000]
        }, index=dates)

        # 2. 构造信号
        # T0(1.1)生成信号 -> T0收盘成交 (Price 100)
        # T2(1.3)生成信号 -> T2收盘成交 (Price 110)

        signals = [
            StrategySignal(
                stock_code="600519", direction="BUY", strength=1.0,
                price=100.0, timestamp=dates[0], reason="buy", strategy_id="test"
            ),
            StrategySignal(
                stock_code="600519", direction="SELL", strength=1.0,
                price=110.0, timestamp=dates[2], reason="sell", strategy_id="test"
            )
        ]

        config = BacktestConfig(initial_capital=10000.0, commission_rate=0.0, stamp_duty=0.0) # 无佣金无印花税

        # 3. 运行模拟
        trades, equity = engine._simulate_trading(signals, data, config)

        # 验证交易
        assert len(trades) == 2
        buy = trades[0]
        sell = trades[1]

        assert buy.direction == "BUY"
        assert buy.price == 100.0
        assert buy.volume == 100 # 10000 / 100 = 100股

        assert sell.direction == "SELL"
        assert sell.price == 110.0
        assert sell.realized_pnl == (110 - 100) * 100 # 1000 profit

        # 验证净值
        final_equity = equity[-1]['value']
        # 初始10000 -> 买入100股花费10000 -> 剩余0现金
        # T1价格105 -> 市值10500 -> 净值10500
        # T2价格110 -> 卖出得到11000 -> 现金11000 -> 净值11000
        # T3价格100 -> 空仓 -> 现金11000 -> 净值11000

        assert final_equity == 11000.0

    @pytest.mark.asyncio
    async def test_run_integration(self):
        """Mock完整运行流程"""
        # Mock Registry
        engine = BacktestEngine(data_provider=None)
        mock_strategy = AsyncMock(spec=BaseStrategy)
        mock_strategy.name = "mock_strat"
        mock_strategy.is_initialized = False

        # Mock _generate_signals
        engine.registry.get = MagicMock(return_value=mock_strategy)
        engine._generate_signals = AsyncMock(return_value=[])
        # 返回空信号，至少跑通流程

        dates = pd.date_range(start='2025-01-01', periods=2)
        data = pd.DataFrame({'close': [10, 11]}, index=dates)

        result = await engine.run(
            strategy_id="test", stock_code="600519",
            start_date=dates[0], end_date=dates[-1],
            data=data
        )

        assert result.strategy_id == "test"
        assert result.metrics.total_return == 0.0

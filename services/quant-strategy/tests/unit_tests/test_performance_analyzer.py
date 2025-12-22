"""Performance Analyzer Tests"""

from datetime import datetime

from backtest.analyzer import PerformanceAnalyzer
from backtest.models import TradeRecord


class TestPerformanceAnalyzer:

    def test_calculate_profit(self):
        """测试盈利情况下的指标计算"""
        # 模拟净值曲线: 1.0 -> 1.1 (10% return)
        equity_curve = [
            {'date': datetime(2025, 1, 1), 'value': 100000.0},
            {'date': datetime(2025, 1, 2), 'value': 105000.0},
            {'date': datetime(2025, 1, 3), 'value': 110000.0}
        ]

        trades = [
            TradeRecord(
                stock_code="600519", direction="BUY", price=100, volume=100,
                amount=10000, commission=5, tax=0,
                timestamp=datetime(2025,1,1), strategy_id="test", reason="buy"
            ),
            TradeRecord(
                stock_code="600519", direction="SELL", price=110, volume=100,
                amount=11000, commission=5, tax=10,
                timestamp=datetime(2025,1,3), strategy_id="test", reason="sell",
                realized_pnl=980
            )
        ]

        metrics = PerformanceAnalyzer.calculate(equity_curve, trades)

        assert metrics.total_return == 0.1
        assert metrics.max_drawdown == 0.0
        assert metrics.total_trades == 2

    def test_calculate_drawdown(self):
        """测试回撤计算"""
        # 1.0 -> 1.2 -> 0.9 -> 1.0
        # Peak 1.2, Trough 0.9, DD = (0.9-1.2)/1.2 = -0.25
        equity_curve = [
            {'date': datetime(2025, 1, 1), 'value': 100.0},
            {'date': datetime(2025, 1, 2), 'value': 120.0},
            {'date': datetime(2025, 1, 3), 'value': 90.0},
            {'date': datetime(2025, 1, 4), 'value': 100.0}
        ]

        metrics = PerformanceAnalyzer.calculate(equity_curve, [])
        assert metrics.max_drawdown == 0.25

    def test_empty_case(self):
        metrics = PerformanceAnalyzer.calculate([], [])
        assert metrics.total_return == 0.0

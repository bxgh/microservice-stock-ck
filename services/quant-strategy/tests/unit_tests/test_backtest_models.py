"""Backtest Models Tests"""

import pytest
from datetime import datetime
from backtest.models import BacktestResult, BacktestConfig, PerformanceMetrics, TradeRecord

class TestBacktestConfig:
    def test_default_config(self):
        config = BacktestConfig()
        assert config.initial_capital == 100000.0
        assert config.commission_rate == 0.0003
        assert config.risk_free_rate == 0.03

    def test_invalid_config(self):
        with pytest.raises(ValueError):
            BacktestConfig(initial_capital=-100)
            
        with pytest.raises(ValueError):
            BacktestConfig(commission_rate=0.2) # Too high

class TestBacktestResult:
    def test_serialization(self):
        metrics = PerformanceMetrics(
            total_return=0.1, annualized_return=0.2, max_drawdown=0.05,
            sharpe_ratio=1.5, volatility=0.1, win_rate=0.6,
            total_trades=10, winning_trades=6, losing_trades=4
        )
        
        result = BacktestResult(
            strategy_id="test_strat",
            stock_code="600519",
            start_date=datetime(2025,1,1),
            end_date=datetime(2025,12,31),
            initial_capital=100000,
            final_capital=110000,
            metrics=metrics,
            equity_curve=[{'date': datetime(2025,1,1), 'value': 100000}],
            trades=[],
            config=BacktestConfig()
        )
        
        json_dict = result.model_dump()
        assert json_dict['strategy_id'] == "test_strat"
        assert json_dict['metrics']['total_return'] == 0.1

"""Risk Control Tests"""

from datetime import datetime

import pytest

# Create a mock Signal class for testing if needed, or import the real one
try:
    from strategies.signal import Signal
except ImportError:
    # Minimal mock if import fails (should not happen in proper env)
    class Signal:
        def __init__(self, stock_code, direction, strength, price, timestamp, reason):
            self.stock_code = stock_code
            self.direction = direction
            self.strength = strength
            self.price = price
            self.timestamp = timestamp
            self.reason = reason
        def __str__(self):
            return f"{self.stock_code}"

from core.risk import RiskManager
from strategies.rules import PriceLimitRule, StaticBlacklistRule, TradingHoursRule


class TestRiskControl:

    @classmethod
    def setup_class(cls):
        # Ensure we start with a clean manager
        manager = RiskManager()
        manager.clear_rules()

    def setup_method(self):
        manager = RiskManager()
        manager.clear_rules()

    @pytest.mark.asyncio
    async def test_blacklist_rule(self):
        rule = StaticBlacklistRule(blacklist=["000001", "600519"])

        # Test blocked
        sig_blocked = Signal(
            stock_code="600519",
            direction="BUY",
            strength="STRONG",
            price=100.0,
            timestamp=datetime.now(),
            reason="test"
        )
        assert await rule.check(sig_blocked) is False

        # Test allowed
        sig_allowed = Signal(
            stock_code="000002",
            direction="BUY",
            strength="STRONG",
            price=100.0,
            timestamp=datetime.now(),
            reason="test"
        )
        assert await rule.check(sig_allowed) is True

    @pytest.mark.asyncio
    async def test_trading_hours_rule(self):
        rule = TradingHoursRule()

        # Mock times
        # 10:00 (Trading)
        timestamp_trading = datetime(2023, 1, 1, 10, 0, 0)
        sig_trading = Signal(
            stock_code="000001",
            direction="BUY",
            strength="STRONG",
            price=10.0,
            timestamp=timestamp_trading.isoformat(),
            reason="test"
        )
        assert await rule.check(sig_trading) is True

        # 12:00 (Break)
        timestamp_break = datetime(2023, 1, 1, 12, 0, 0)
        sig_break = Signal(
            stock_code="000001",
            direction="BUY",
            strength="STRONG",
            price=10.0,
            timestamp=timestamp_break.isoformat(),
            reason="test"
        )
        assert await rule.check(sig_break) is False

        # 16:00 (Closed)
        timestamp_closed = datetime(2023, 1, 1, 16, 0, 0)
        sig_closed = Signal(
            stock_code="000001",
            direction="BUY",
            strength="STRONG",
            price=10.0,
            timestamp=timestamp_closed.isoformat(),
            reason="test"
        )
        assert await rule.check(sig_closed) is False

    @pytest.mark.asyncio
    async def test_risk_manager_flow(self):
        manager = RiskManager()
        manager.add_rule(StaticBlacklistRule(blacklist=["000001"]))
        manager.add_rule(PriceLimitRule())

        # Case 1: All pass
        sig_pass = Signal(
            stock_code="000002",
            direction="BUY",
            strength="STRONG",
            price=10.0,
            timestamp=datetime.now(),
            reason="test"
        )
        assert await manager.validate(sig_pass) is True

        # Case 2: Blacklist fail
        sig_fail_blacklist = Signal(
            stock_code="000001",
            direction="BUY",
            strength="STRONG",
            price=10.0,
            timestamp=datetime.now(),
            reason="test"
        )
        assert await manager.validate(sig_fail_blacklist) is False

        # Case 3: Price fail
        sig_fail_price = Signal(
            stock_code="000002",
            direction="BUY",
            strength="STRONG",
            price=-1.0,
            timestamp=datetime.now(),
            reason="test"
        )
        assert await manager.validate(sig_fail_price) is False

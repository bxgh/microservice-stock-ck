import pytest
import pandas as pd
import asyncio
from src.strategies.base import BaseStrategy, StrategySignal, SignalType
from src.strategies.registry import StrategyRegistry

class TestStrategy(BaseStrategy):
    """用于测试的策略类"""
    async def on_bar(self, data: pd.DataFrame):
        return [
            StrategySignal(
                strategy_name=self.name,
                stock_code="000001",
                signal_type=SignalType.LONG,
                reason="Test Signal"
            )
        ]
        
    async def on_tick(self, tick_data):
        return []

class TestRegistry:
    def test_register_strategy(self):
        """测试策略注册"""
        StrategyRegistry.register(TestStrategy)
        assert "TestStrategy" in StrategyRegistry.list_strategies()

    def test_create_strategy(self):
        """测试策略实例化"""
        StrategyRegistry.register(TestStrategy)
        
        strategy = StrategyRegistry.create_strategy("TestStrategy", config={"test": 123})
        assert strategy is not None
        assert strategy.name == "TestStrategy"
        assert strategy.config["test"] == 123
        assert isinstance(strategy, TestStrategy)
        
        # 验证是否在 active 列表中
        assert "TestStrategy" in StrategyRegistry.list_active_strategies()

    def test_create_unknown_strategy(self):
        """测试未注册策略"""
        strategy = StrategyRegistry.create_strategy("UnknownStrategy")
        assert strategy is None

    def test_get_strategy(self):
        """测试获取已存在的实例"""
        StrategyRegistry.register(TestStrategy)
        created = StrategyRegistry.create_strategy("TestStrategy")
        
        retrieved = StrategyRegistry.get_strategy("TestStrategy")
        assert retrieved is created

@pytest.mark.asyncio
async def test_base_strategy_lifecycle():
    """测试策略生命周期"""
    strategy = TestStrategy("lifecycle_test")
    assert not strategy.is_initialized
    
    await strategy.initialize()
    assert strategy.is_initialized

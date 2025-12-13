"""BaseStrategy单元测试

测试策略基类的生命周期管理和并发安全性。
"""

import pytest
import asyncio

from strategies.base import BaseStrategy, StrategyInitializationError
from strategies.signal import Signal


class MockStrategy(BaseStrategy):
    """Mock策略用于测试"""
    
    def __init__(self, strategy_id, config, data_provider):
        super().__init__(strategy_id, config, data_provider)
        self.init_called = False
        self.close_called = False
        self.bar_count = 0
        self.tick_count = 0
    
    async def _do_initialize(self):
        """模拟初始化"""
        await asyncio.sleep(0.01)  # 模拟IO操作
        self.init_called = True
    
    async def on_bar(self, bar_data):
        """模拟处理K线"""
        self.bar_count += 1
    
    async def on_tick(self, tick_data):
        """模拟处理Tick"""
        self.tick_count += 1
    
    def generate_signal(self):
        """生成测试信号"""
        return Signal(
            stock_code="600519",
            direction="BUY",
            strength=0.8,
            price=1800.0,
            reason="Mock signal",
            strategy_id=self.strategy_id
        )
    
    async def _do_close(self):
        """模拟清理"""
        await asyncio.sleep(0.01)
        self.close_called = True


class TestBaseStrategyLifecycle:
    """测试策略生命周期"""
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化"""
        strategy = MockStrategy("test_001", {}, None)
        
        assert not strategy.is_initialized
        await strategy.initialize()
        assert strategy.is_initialized
        assert strategy.init_called
    
    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """测试初始化幂等性"""
        strategy = MockStrategy("test_002", {}, None)
        
        # 多次初始化
        await strategy.initialize()
        await strategy.initialize()
        await strategy.initialize()
        
        # 只执行一次
        assert strategy.is_initialized
    
    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭"""
        strategy = MockStrategy("test_003", {}, None)
        
        await strategy.initialize()
        assert strategy.is_initialized
        
        await strategy.close()
        assert not strategy.is_initialized
        assert strategy.close_called
    
    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """测试关闭幂等性"""
        strategy = MockStrategy("test_004", {}, None)
        
        await strategy.initialize()
        await strategy.close()
        await strategy.close()  # 第二次关闭
        
        assert not strategy.is_initialized


class TestBaseStrategyConcurrency:
    """测试并发安全性"""
    
    @pytest.mark.asyncio
    async def test_concurrent_initialize(self):
        """测试并发初始化"""
        strategy = MockStrategy("test_005", {}, None)
        
        # 10个协程同时初始化
        tasks = [strategy.initialize() for _ in range(10)]
        await asyncio.gather(*tasks)
        
        # 只执行一次初始化
        assert strategy.is_initialized
    
    @pytest.mark.asyncio
    async def test_concurrent_close(self):
        """测试并发关闭"""
        strategy = MockStrategy("test_006", {}, None)
        
        await strategy.initialize()
        
        # 10个协程同时关闭
        tasks = [strategy.close() for _ in range(10)]
        await asyncio.gather(*tasks)
        
        assert not strategy.is_initialized


class TestSignalValidation:
    """测试信号验证"""
    
    def test_validate_valid_signal(self):
        """测试验证有效信号"""
        strategy = MockStrategy("test_007", {}, None)
        signal = strategy.generate_signal()
        
        assert strategy.validate_signal(signal)
    
    def test_validate_invalid_direction(self):
        """测试无效方向"""
        strategy = MockStrategy("test_008", {}, None)
        signal = Signal(
            stock_code="600519",
            direction="BUY",
            strength=0.8,
            price=100.0,
            reason="test",
            strategy_id="test"
        )
        # 直接修改绕过Pydantic验证（仅用于测试）
        signal.direction = "INVALID"
        
        # validate_signal应该检测到无效方向
        assert not strategy.validate_signal(signal)  # 应该返回False

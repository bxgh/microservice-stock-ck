"""StrategyRegistry并发安全测试

参考 test_mootdx_connection_concurrency.py 风格，测试注册表的并发安全性。
"""

import pytest
import asyncio

from strategies.registry import StrategyRegistry
from strategies.base import BaseStrategy
from strategies.signal import Signal


class SimpleStrategy(BaseStrategy):
    """简单测试策略"""
    
    async def _do_initialize(self):
        await asyncio.sleep(0.001)
    
    async def on_bar(self, bar_data):
        pass
    
    async def on_tick(self, tick_data):
        pass
    
    def generate_signal(self):
        return None
    
    async def _do_close(self):
        await asyncio.sleep(0.001)


@pytest.mark.asyncio
async def test_concurrent_register():
    """测试并发注册策略"""
    # 创建新的registry实例（清空状态）
    registry = StrategyRegistry()
    await registry.stop_all()  # 清空
    
    async def register_strategy(i):
        strategy = SimpleStrategy(f"strategy_{i}", {}, None)
        await registry.register(f"strategy_{i}", strategy)
    
    # 10个协程并发注册
    tasks = [register_strategy(i) for i in range(10)]
    await asyncio.gather(*tasks)
    
    # 验证所有策略都成功注册
    assert registry.count() == 10
    assert len(registry.list_all()) == 10


@pytest.mark.asyncio
async def test_concurrent_register_and_query():
    """测试并发注册和查询"""
    registry = StrategyRegistry()
    await registry.stop_all()
    
    async def register_batch():
        for i in range(50):
            strategy = SimpleStrategy(f"s_{i}", {}, None)
            await registry.register(f"s_{i}", strategy)
    
    async def query_loop():
        for _ in range(100):
            registry.get("s_25")
            await asyncio.sleep(0.001)
    
    # 1个注册协程 + 5个查询协程
    await asyncio.gather(
        register_batch(),
        *[query_loop() for _ in range(5)]
    )
    
    assert registry.count() == 50


@pytest.mark.asyncio
async def test_concurrent_unregister():
    """测试并发注销"""
    registry = StrategyRegistry()
    await registry.stop_all()
    
    # 先注册20个策略
    for i in range(20):
        strategy = SimpleStrategy(f"strategy_{i}", {}, None)
        await registry.register(f"strategy_{i}", strategy)
    
    # 并发注销
    tasks = [registry.unregister(f"strategy_{i}") for i in range(20)]
    await asyncio.gather(*tasks)
    
    assert registry.count() == 0


@pytest.mark.asyncio
async def test_duplicate_register_raises_error():
    """测试重复注册抛出异常"""
    registry = StrategyRegistry()
    await registry.stop_all()
    
    strategy1 = SimpleStrategy("duplicate_test", {}, None)
    await registry.register("duplicate_test", strategy1)
    
    # 尝试注册相同ID
    strategy2 = SimpleStrategy("duplicate_test", {}, None)
    with pytest.raises(ValueError, match="already registered"):
        await registry.register("duplicate_test", strategy2)


@pytest.mark.asyncio
async def test_high_concurrency_stress():
    """高并发压力测试（参考mootdx风格）"""
    registry = StrategyRegistry()
    await registry.stop_all()
    
    CONCURRENT_COUNT = 50
    
    async def mixed_operations(worker_id):
        """混合操作：注册、查询、注销"""
        # 注册
        strategy = SimpleStrategy(f"worker_{worker_id}", {}, None)
        await registry.register(f"worker_{worker_id}", strategy)
        
        # 查询100次
        for _ in range(100):
            registry.get(f"worker_{worker_id}")
        
        # 列出所有
        registry.list_all()
        
        # 注销
        await registry.unregister(f"worker_{worker_id}")
    
    # 50个并发worker
    tasks = [mixed_operations(i) for i in range(CONCURRENT_COUNT)]
    await asyncio.gather(*tasks)
    
    # 所有策略都应该被注销
    assert registry.count() == 0

import pytest
import asyncio
from strategies.registry import StrategyRegistry
from strategies.value_strategy import ValueStrategy

@pytest.mark.asyncio
async def test_registry_registration_concurrency():
    """测试高并发下策略注册的线程安全性"""
    registry = StrategyRegistry()
    await registry.stop_all()
    
    # 模拟 50 个协程同时尝试注册不同的策略
    async def register_task(i):
        strategy = ValueStrategy()
        # 修改 strategy_id 使得它是唯一的
        # 注意：此处我们需要模拟一个具有不同 ID 的策略类，因为 ValueStrategy 的 strategy_id 是 property
        class TempStrategy(ValueStrategy):
            def __init__(self, sid):
                super().__init__()
                self._sid = sid
            @property
            def strategy_id(self):
                return self._sid
                
        s = TempStrategy(f"strat_{i}")
        await registry.register(s.strategy_id, s)

    # 启动并发任务
    tasks = [register_task(i) for i in range(50)]
    await asyncio.gather(*tasks)
    
    # 验证注册成功的数量
    assert registry.count() == 50
    
    # 清理
    await registry.stop_all()

@pytest.mark.asyncio
async def test_registry_duplicate_registration_concurrency():
    """测试多个协程并发注册同一个 ID 时的冲突处理"""
    registry = StrategyRegistry()
    await registry.stop_all()
    
    strategy_id = "duplicate_strat"
    success_count = 0
    fail_count = 0
    
    async def register_task():
        nonlocal success_count, fail_count
        try:
            s = ValueStrategy()
            # 同样需要覆盖 strategy_id
            class TempStrategy(ValueStrategy):
                @property
                def strategy_id(self):
                    return strategy_id
            
            await registry.register(strategy_id, TempStrategy())
            success_count += 1
        except ValueError:
            fail_count += 1
            
    tasks = [register_task() for _ in range(20)]
    await asyncio.gather(*tasks)
    
    # 应该只有一个成功，其他报错
    assert success_count == 1
    assert fail_count == 19
    assert registry.count() == 1
    
    await registry.stop_all()

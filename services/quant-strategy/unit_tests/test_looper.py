import pytest
import asyncio
from src.core.looper import InternalLooper

class TestInternalLooper:
    @pytest.mark.asyncio
    async def test_looper_lifecycle(self):
        """测试循环器的启动和停止"""
        looper = InternalLooper()
        counter = {"count": 0}
        
        async def increment():
            counter["count"] += 1
            
        # 添加一个极短间隔的任务 (0.1s)
        looper.add_loop(increment, 0.1, "TestTask")
        
        await looper.start()
        # 让它运行一小会儿
        await asyncio.sleep(0.35)
        
        await looper.stop()
        
        # 验证是否执行了至少 3 次
        assert counter["count"] >= 3
        
    def test_add_loop(self):
        """测试添加任务"""
        looper = InternalLooper()
        async def dummy(): pass
        
        looper.add_loop(dummy, 10, "Dummy")
        assert len(looper._loops) == 1
        assert looper._loops[0]["name"] == "Dummy"
        assert looper._loops[0]["interval"] == 10

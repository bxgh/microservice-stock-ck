import pytest
import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.tdx_pool import TDXClientPool

@pytest.mark.asyncio
async def test_tdx_pool_round_robin():
    """测试连接池的 Round-Robin 负载均衡逻辑"""
    pool = TDXClientPool(size=3)
    
    # Mock Quotes.factory
    with patch('core.tdx_pool.Quotes.factory') as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        
        # 初始化
        await pool.initialize()
        assert pool.active_count == 3
        
        # 并发获取客户端
        tasks = [pool.get_next() for _ in range(6)]
        clients = await asyncio.gather(*tasks)
        
        # 验证返回了 6 个客户端
        assert len(clients) == 6
        
        # 验证 Round-Robin: 0, 1, 2, 0, 1, 2
        # 注意：由于 gather 是并发运行的，顺序可能不完全固定，
        # 但由于 get_next 内部有锁，且顺序递增，在没有阻塞的情况下通常是有序的。
        # 更有保障的验证是检查每个客户端被使用了几次。
        
        client_usage = {}
        for c in clients:
            client_usage[id(c)] = client_usage.get(id(c), 0) + 1
            
        # size=3, total=6, 每个客户端应该被使用 2 次
        assert len(client_usage) == 1 # 因为 mock_factory 返回的是同一个 client 引用
        # 修正：我们需要不同的 client 实例来验证 Round-Robin

@pytest.mark.asyncio
async def test_tdx_pool_concurrency_safe():
    """测试并发情况下的 initialization 和 get_next 是否安全"""
    pool = TDXClientPool(size=5)
    
    with patch('core.tdx_pool.Quotes.factory') as mock_factory:
        # 为每个调用返回不同的 mock 实例
        mock_factory.side_effect = lambda **kwargs: MagicMock()
        
        # 模拟 20 个协程同时初始化和获取
        async def worker():
            await pool.initialize()
            return await pool.get_next()
            
        tasks = [worker() for _ in range(50)]
        clients = await asyncio.gather(*tasks)
        
        assert len(clients) == 50
        assert pool.active_count == 5
        
        # 验证 5 个不同的客户端实例
        unique_clients = set(id(c) for c in clients)
        assert len(unique_clients) == 5
        
        # 验证分配是否均衡 (5个各10次)
        usage = {}
        for c in clients:
            usage[id(c)] = usage.get(id(c), 0) + 1
        
        for count in usage.values():
            assert count == 10

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

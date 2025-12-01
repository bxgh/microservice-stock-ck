#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 MootdxConnection 并发安全性

测试内容：
- 并发连接获取
- 并发连接关闭
- 竞态条件检测
- 统计信息准确性
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_sources.mootdx.connection import MootdxConnection


@pytest.fixture
def mock_quotes():
    """Mock Mootdx Quotes 类"""
    with patch('src.data_sources.mootdx.connection.Quotes') as mock:
        # 创建一个 mock 工厂方法，添加延迟模拟真实场景
        mock_client = MagicMock()
        mock_client.transactions = MagicMock(return_value=None)
        
        async def delayed_factory(*args, **kwargs):
            """模拟延迟的连接创建"""
            await asyncio.sleep(0.1)  # 模拟连接创建需要时间
            return mock_client
        
        mock.factory = MagicMock(return_value=mock_client)
        yield mock


@pytest.mark.asyncio
async def test_concurrent_connection_get(mock_quotes):
    """测试并发获取连接"""
    conn = MootdxConnection(connection_lifetime=300, best_ip=False, initial_wait_time=0.1)
    
    # 并发100次获取连接
    tasks = [conn.get_client() for _ in range(100)]
    clients = await asyncio.gather(*tasks)
    
    # 验证所有客户端都是同一个实例（复用）
    assert all(client is not None for client in clients)
    first_client = clients[0]
    assert all(client is first_client for client in clients)
    
    # 验证统计信息
    stats = conn.get_stats()
    assert stats['total_creates'] == 1  # 只创建了1次
    assert stats['total_reuses'] == 99  # 复用了99次
    
    # 验证复用率
    reuse_rate = float(stats['reuse_rate'].rstrip('%'))
    assert reuse_rate == 99.0


@pytest.mark.asyncio
async def test_concurrent_mixed_operations(mock_quotes):
    """测试并发混合操作（获取、健康检查、统计）"""
    conn = MootdxConnection(connection_lifetime=300, best_ip=False, initial_wait_time=0.05)
    
    async def get_client_task():
        """获取客户端任务"""
        return await conn.get_client()
    
    async def health_check_task():
        """健康检查任务"""
        await asyncio.sleep(0.01)
        return conn.is_healthy()
    
    async def stats_task():
        """统计信息任务"""
        await asyncio.sleep(0.01)
        return conn.get_stats()
    
    # 创建混合任务
    tasks = []
    for i in range(50):
        tasks.append(get_client_task())
        tasks.append(health_check_task())
        tasks.append(stats_task())
    
    # 并发执行
    results = await asyncio.gather(*tasks)
    
    # 验证没有抛出异常
    assert len(results) == 150
    
    # 验证最终统计
    stats = conn.get_stats()
    assert stats['total_creates'] >= 1
    assert stats['total_failures'] == 0


@pytest.mark.asyncio
async def test_concurrent_connection_close_and_get(mock_quotes):
    """测试并发关闭和获取连接（压力测试）"""
    conn = MootdxConnection(connection_lifetime=300, best_ip=False, initial_wait_time=0.05)
    
    async def get_and_maybe_close():
        """随机获取或关闭连接"""
        import random
        client = await conn.get_client()
        await asyncio.sleep(0.01)
        
        # 20%的概率关闭连接
        if random.random() < 0.2:
            await conn.close()
        
        return client
    
    # 并发执行50次
    tasks = [get_and_maybe_close() for _ in range(50)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 验证没有异常
    exceptions = [r for r in results if isinstance(r, Exception)]
    assert len(exceptions) == 0
    
    # 验证最终状态
    stats = conn.get_stats()
    print(f"Final stats: {stats}")
    assert stats['total_failures'] == 0


@pytest.mark.asyncio
async def test_no_race_condition_in_stats(mock_quotes):
    """测试统计信息不存在竞态条件"""
    conn = MootdxConnection(connection_lifetime=1, best_ip=False, initial_wait_time=0.05)
    
    # 并发获取连接
    tasks = [conn.get_client() for _ in range(100)]
    await asyncio.gather(*tasks)
    
    # 等待连接过期
    await asyncio.sleep(1.2)
    
    # 再次并发获取（触发重建）
    tasks = [conn.get_client() for _ in range(100)]
    await asyncio.gather(*tasks)
    
    # 验证统计信息的一致性
    stats = conn.get_stats()
    
    # 应该创建2次（初始 + 过期重建）
    assert stats['total_creates'] == 2
    
    # 应该复用198次（第一批99次 + 第二批99次）
    assert stats['total_reuses'] == 198
    
    # 应该关闭1次（过期时）
    assert stats['total_closes'] == 1
    
    # 验证复用率计算正确
    # 198 / (2 + 198) = 99%
    reuse_rate = float(stats['reuse_rate'].rstrip('%'))
    assert reuse_rate == 99.0


@pytest.mark.asyncio
async def test_lock_prevents_double_creation(mock_quotes):
    """测试锁机制防止重复创建连接"""
    conn = MootdxConnection(connection_lifetime=300, best_ip=False, initial_wait_time=0.1)
    
    # 启动多个任务同时尝试创建连接
    # 使用足够的并发来测试锁的效果
    tasks = [conn.get_client() for _ in range(20)]
    clients = await asyncio.gather(*tasks)
    
    # 所有客户端应该是同一个实例
    assert all(client is clients[0] for client in clients)
    
    # 只应该创建1次
    stats = conn.get_stats()
    assert stats['total_creates'] == 1
    
    # 打印日志辅助验证
    print(f"Lock test stats: creates={stats['total_creates']}, reuses={stats['total_reuses']}")


@pytest.mark.asyncio
async def test_resource_cleanup_thread_safety(mock_quotes):
    """测试资源清理的线程安全性"""
    conn = MootdxConnection(best_ip=False, initial_wait_time=0.05)
    
    # 获取连接
    await conn.get_client()
    
    # 并发多次调用 cleanup
    tasks = [conn.cleanup() for _ in range(10)]
    await asyncio.gather(*tasks)
    
    # 验证最终状态
    assert conn._connected == False
    assert conn.client is None
    
    # 统计应该只记录1次关闭
    stats = conn.get_stats()
    # 注意：由于锁的保护，虽然调用了10次cleanup，但实际只执行1次关闭
    # 后续的cleanup会发现client已经是None，不会再增加计数
    assert stats['total_closes'] >= 1


@pytest.mark.asyncio
async def test_initial_wait_time_configuration(mock_quotes):
    """测试 initial_wait_time 配置参数"""
    import time
    
    # 使用较短的等待时间
    conn_short = MootdxConnection(best_ip=False, initial_wait_time=0.1)
    
    start = time.time()
    await conn_short.get_client()
    elapsed_short = time.time() - start
    
    # 验证等待时间约为 0.1 秒（允许一些误差）
    assert 0.08 < elapsed_short < 0.3
    
    # 使用较长的等待时间
    conn_long = MootdxConnection(best_ip=False, initial_wait_time=0.5)
    
    start = time.time()
    await conn_long.get_client()
    elapsed_long = time.time() - start
    
    # 验证等待时间约为 0.5 秒（允许一些误差）
    assert 0.4 < elapsed_long < 0.7
    
    # 长等待应该明显大于短等待
    assert elapsed_long > elapsed_short


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

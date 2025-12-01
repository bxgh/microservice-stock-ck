#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 MootdxConnection 连接复用功能

测试内容：
- 连接创建
- 连接复用
- 连接过期重建
- 连接关闭
- 高复用率验证
- 统计信息
"""

import pytest
import asyncio
from datetime import datetime, timedelta
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
        # 创建一个 mock 工厂方法
        mock_client = MagicMock()
        mock_client.transactions = MagicMock(return_value=None)
        mock.factory = MagicMock(return_value=mock_client)
        yield mock


@pytest.mark.asyncio
async def test_connection_creation(mock_quotes):
    """测试连接创建"""
    conn = MootdxConnection(connection_lifetime=300, best_ip=False)
    
    client = await conn.get_client()
    assert client is not None
    assert conn._connected == True
    assert conn._connect_time is not None
    
    stats = conn.get_stats()
    assert stats['total_creates'] == 1
    assert stats['total_reuses'] == 0
    assert stats['reuse_rate'] == '0.0%'


@pytest.mark.asyncio
async def test_connection_reuse(mock_quotes):
    """测试连接复用"""
    conn = MootdxConnection(connection_lifetime=300, best_ip=False)
    
    # 第一次获取
    client1 = await conn.get_client()
    first_create_time = conn._connect_time
    
    # 第二次获取（应该复用）
    await asyncio.sleep(0.1)
    client2 = await conn.get_client()
    
    assert client1 is client2  # 同一个实例
    assert conn._connect_time == first_create_time  # 连接时间未变
    
    stats = conn.get_stats()
    assert stats['total_creates'] == 1
    assert stats['total_reuses'] == 1
    assert '50.0%' in stats['reuse_rate']  # 1次创建 + 1次复用 = 50%


@pytest.mark.asyncio
async def test_connection_expiry(mock_quotes):
    """测试连接过期重建"""
    conn = MootdxConnection(connection_lifetime=1, best_ip=False)  # 1秒过期
    
    # 创建连接
    client1 = await conn.get_client()
    first_create_time = conn._connect_time
    
    # 等待过期
    await asyncio.sleep(1.2)
    
    # 重新获取（应该创建新连接）
    client2 = await conn.get_client()
    
    assert conn._connect_time != first_create_time  # 连接时间已更新
    stats = conn.get_stats()
    assert stats['total_creates'] == 2  # 创建了2次
    assert stats['total_closes'] == 1  # 关闭了1次


@pytest.mark.asyncio
async def test_connection_close(mock_quotes):
    """测试连接关闭"""
    conn = MootdxConnection(best_ip=False)
    
    await conn.get_client()
    assert conn._connected == True
    
    await conn.close()
    assert conn._connected == False
    assert conn.client is None
    
    stats = conn.get_stats()
    assert stats['total_closes'] == 1


@pytest.mark.asyncio
async def test_high_reuse_rate(mock_quotes):
    """测试高复用率"""
    conn = MootdxConnection(connection_lifetime=300, best_ip=False)
    
    # 连续100次获取
    for i in range(100):
        client = await conn.get_client()
        assert client is not None
    
    stats = conn.get_stats()
    assert stats['total_creates'] == 1
    assert stats['total_reuses'] == 99
    
    # 复用率应该 > 90%
    reuse_rate = float(stats['reuse_rate'].rstrip('%'))
    assert reuse_rate > 90.0
    assert reuse_rate == 99.0  # 99/100 = 99%


@pytest.mark.asyncio
async def test_backward_compatible_connect(mock_quotes):
    """测试向后兼容的 connect() 方法"""
    conn = MootdxConnection(best_ip=False)
    
    # 使用旧的 connect() 方法
    result = await conn.connect()
    assert result == True
    assert conn.is_connected == True
    
    # 再次调用应该复用
    result2 = await conn.connect()
    assert result2 == True
    
    stats = conn.get_stats()
    assert stats['total_creates'] == 1
    assert stats['total_reuses'] == 1


@pytest.mark.asyncio
async def test_connection_age(mock_quotes):
    """测试连接年龄计算"""
    conn = MootdxConnection(best_ip=False)
    
    # 未连接时
    assert conn._get_connection_age() is None
    
    # 连接后
    await conn.get_client()
    await asyncio.sleep(0.5)
    
    age = conn._get_connection_age()
    assert age is not None
    assert age >= 0.5
    assert age < 1.0


@pytest.mark.asyncio
async def test_stats_tracking(mock_quotes):
    """测试统计信息追踪"""
    conn = MootdxConnection(connection_lifetime=1, best_ip=False)
    
    # 创建连接
    await conn.get_client()
    
    # 复用几次
    for _ in range(5):
        await conn.get_client()
    
    # 等待过期并重建
    await asyncio.sleep(1.2)
    await conn.get_client()
    
    # 再复用几次
    for _ in range(3):
        await conn.get_client()
    
    stats = conn.get_stats()
    assert stats['total_creates'] == 2  # 创建了2次
    assert stats['total_reuses'] == 8   # 复用了8次
    assert stats['total_closes'] == 1   # 关闭了1次（过期重建时）
    assert stats['is_connected'] == True
    
    # 验证复用率计算
    # (8 reuses) / (2 creates + 8 reuses) = 80%
    reuse_rate = float(stats['reuse_rate'].rstrip('%'))
    assert reuse_rate == 80.0


@pytest.mark.asyncio
async def test_connection_failure_handling(mock_quotes):
    """测试连接失败处理"""
    # 模拟连接失败
    mock_quotes.factory.side_effect = Exception("Connection failed")
    
    conn = MootdxConnection(best_ip=False)
    client = await conn.get_client()
    
    assert client is None
    assert conn._connected == False
    
    stats = conn.get_stats()
    assert stats['total_failures'] == 1


@pytest.mark.asyncio
async def test_properties(mock_quotes):
    """测试属性访问"""
    conn = MootdxConnection(best_ip=False)
    
    # 未连接时
    assert conn.is_connected == False
    assert conn.connect_time is None
    
    # 连接后
    await conn.get_client()
    assert conn.is_connected == True
    assert conn.connect_time is not None
    assert isinstance(conn.connect_time, datetime)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

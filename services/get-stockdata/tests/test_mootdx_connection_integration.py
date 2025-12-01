#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试：验证 MootdxConnection 在实际使用场景中的连接复用效果

测试场景：
- 模拟连续100次数据获取请求
- 验证连接复用率 > 90%
- 验证连接过期后自动重建
- 验证性能提升
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_sources.mootdx.connection import MootdxConnection


@pytest.fixture
def mock_quotes_with_data():
    """Mock Mootdx Quotes 类，返回模拟数据"""
    with patch('src.data_sources.mootdx.connection.Quotes') as mock:
        # 创建一个 mock 客户端
        mock_client = MagicMock()
        
        # 模拟 transactions 方法返回数据
        def mock_transactions(symbol, date, start, count):
            # 返回模拟的分笔数据
            return pd.DataFrame({
                'time': ['09:30:00', '09:30:01', '09:30:02'],
                'price': [10.5, 10.51, 10.52],
                'volume': [100, 200, 150],
                'buyorsell': [1, 0, 2]
            })
        
        mock_client.transactions = mock_transactions
        mock.factory = MagicMock(return_value=mock_client)
        yield mock


@pytest.mark.asyncio
async def test_continuous_data_fetching_with_reuse(mock_quotes_with_data):
    """
    测试连续数据获取场景下的连接复用
    
    场景：连续获取100次数据，验证复用率 > 90%
    """
    conn = MootdxConnection(connection_lifetime=300, best_ip=False)
    
    print("\n" + "="*60)
    print("🧪 测试场景：连续100次数据获取")
    print("="*60)
    
    start_time = time.time()
    
    # 连续获取100次数据
    for i in range(100):
        client = await conn.get_client()
        assert client is not None
        
        # 模拟实际使用：调用 fetch_transactions
        df = conn.fetch_transactions('000001', '20251129', 0, 800)
        assert not df.empty
        
        if (i + 1) % 20 == 0:
            stats = conn.get_stats()
            print(f"  进度: {i+1}/100, 复用率: {stats['reuse_rate']}")
    
    elapsed = time.time() - start_time
    
    # 获取最终统计
    stats = conn.get_stats()
    
    print("\n" + "="*60)
    print("📊 测试结果")
    print("="*60)
    print(f"  总请求次数: 100")
    print(f"  连接创建次数: {stats['total_creates']}")
    print(f"  连接复用次数: {stats['total_reuses']}")
    print(f"  连接复用率: {stats['reuse_rate']}")
    print(f"  总耗时: {elapsed:.2f}s")
    print(f"  平均每次: {elapsed/100*1000:.2f}ms")
    print("="*60)
    
    # 验收标准
    assert stats['total_creates'] == 1, "应该只创建1次连接"
    assert stats['total_reuses'] == 99, "应该复用99次"
    
    reuse_rate = float(stats['reuse_rate'].rstrip('%'))
    assert reuse_rate > 90.0, f"复用率应该 > 90%，实际: {reuse_rate}%"
    assert reuse_rate == 99.0, f"复用率应该是99%，实际: {reuse_rate}%"


@pytest.mark.asyncio
async def test_connection_recreation_after_expiry(mock_quotes_with_data):
    """
    测试连接过期后的自动重建
    
    场景：
    1. 获取50次数据（使用同一连接）
    2. 等待连接过期
    3. 再获取50次数据（应该重建连接）
    """
    conn = MootdxConnection(connection_lifetime=2, best_ip=False)  # 2秒过期
    
    print("\n" + "="*60)
    print("🧪 测试场景：连接过期自动重建")
    print("="*60)
    
    # 第一阶段：获取50次数据
    print("\n📥 第一阶段：获取50次数据...")
    for i in range(50):
        client = await conn.get_client()
        df = conn.fetch_transactions('000001', '20251129', 0, 800)
        assert not df.empty
    
    stats_phase1 = conn.get_stats()
    print(f"  阶段1统计: 创建={stats_phase1['total_creates']}, 复用={stats_phase1['total_reuses']}")
    
    # 等待连接过期
    print("\n⏳ 等待连接过期（2.5秒）...")
    await asyncio.sleep(2.5)
    
    # 第二阶段：再获取50次数据
    print("\n📥 第二阶段：再获取50次数据...")
    for i in range(50):
        client = await conn.get_client()
        df = conn.fetch_transactions('000001', '20251129', 0, 800)
        assert not df.empty
    
    stats_phase2 = conn.get_stats()
    
    print("\n" + "="*60)
    print("📊 测试结果")
    print("="*60)
    print(f"  第一阶段: 创建={stats_phase1['total_creates']}, 复用={stats_phase1['total_reuses']}")
    print(f"  第二阶段: 创建={stats_phase2['total_creates']}, 复用={stats_phase2['total_reuses']}")
    print(f"  总复用率: {stats_phase2['reuse_rate']}")
    print("="*60)
    
    # 验收标准
    assert stats_phase2['total_creates'] == 2, "应该创建2次连接（初始+过期重建）"
    assert stats_phase2['total_reuses'] == 98, "应该复用98次"
    assert stats_phase2['total_closes'] == 1, "应该关闭1次连接（过期时）"


@pytest.mark.asyncio
async def test_performance_comparison(mock_quotes_with_data):
    """
    测试性能对比：验证连接复用的效果
    
    对比指标：连接创建次数
    """
    print("\n" + "="*60)
    print("🧪 测试场景：连接复用效果验证")
    print("="*60)
    
    # 使用连接复用
    print("\n📊 使用连接复用（100次请求）")
    conn = MootdxConnection(connection_lifetime=300, best_ip=False)
    
    start_time = time.time()
    for i in range(100):
        client = await conn.get_client()
        df = conn.fetch_transactions('000001', '20251129', 0, 800)
    elapsed = time.time() - start_time
    
    stats = conn.get_stats()
    print(f"  耗时: {elapsed:.3f}s")
    print(f"  复用率: {stats['reuse_rate']}")
    print(f"  创建次数: {stats['total_creates']}")
    
    print("\n" + "="*60)
    print("📊 测试结果")
    print("="*60)
    print(f"  总请求: 100次")
    print(f"  连接创建: {stats['total_creates']}次")
    print(f"  连接复用: {stats['total_reuses']}次")
    print(f"  复用率: {stats['reuse_rate']}")
    print(f"  节省创建: {100 - stats['total_creates']}次 ({(100 - stats['total_creates'])/100*100:.0f}%)")
    print("="*60)
    
    # 验证：应该只创建1次连接
    assert stats['total_creates'] == 1, "应该只创建1次连接"
    assert stats['total_reuses'] == 99, "应该复用99次"


@pytest.mark.asyncio
async def test_real_world_scenario(mock_quotes_with_data):
    """
    测试真实世界场景：模拟 SnapshotRecorder 的使用模式
    
    场景：
    - 每3秒采集一次数据
    - 持续采集10轮
    - 连接生命周期5分钟
    """
    conn = MootdxConnection(connection_lifetime=300, best_ip=False)
    
    print("\n" + "="*60)
    print("🧪 测试场景：真实世界使用（模拟快照记录器）")
    print("="*60)
    
    rounds = 10
    interval = 0.1  # 加速测试，实际是3秒
    
    for round_num in range(rounds):
        print(f"\n📸 第 {round_num + 1} 轮采集")
        
        # 获取连接
        client = await conn.get_client()
        
        # 模拟批量获取多只股票
        symbols = ['000001', '000002', '600000', '600036', '601318']
        for symbol in symbols:
            df = conn.fetch_transactions(symbol, '20251129', 0, 800)
            assert not df.empty
        
        stats = conn.get_stats()
        print(f"  已采集 {len(symbols)} 只股票")
        print(f"  当前复用率: {stats['reuse_rate']}")
        print(f"  连接年龄: {stats['connection_age']:.1f}s")
        
        # 等待下一轮
        await asyncio.sleep(interval)
    
    final_stats = conn.get_stats()
    
    print("\n" + "="*60)
    print("📊 最终统计")
    print("="*60)
    print(f"  总采集轮次: {rounds}")
    print(f"  总请求次数: {rounds * len(symbols)}")
    print(f"  连接创建次数: {final_stats['total_creates']}")
    print(f"  连接复用次数: {final_stats['total_reuses']}")
    print(f"  最终复用率: {final_stats['reuse_rate']}")
    print("="*60)
    
    # 验收标准
    assert final_stats['total_creates'] == 1, "应该只创建1次连接"
    reuse_rate = float(final_stats['reuse_rate'].rstrip('%'))
    assert reuse_rate >= 90.0, f"复用率应该 >= 90%，实际: {reuse_rate}%"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

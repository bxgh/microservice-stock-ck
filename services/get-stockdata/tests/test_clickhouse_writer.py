#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ClickHouse Writer 测试
验证盘口快照数据写入功能
"""

import pytest
import os
from datetime import datetime
from src.storage.clickhouse_writer import ClickHouseWriter, SnapshotData


class TestClickHouseWriter:
    """测试 ClickHouseWriter 类"""
    
    @pytest.fixture
    def writer(self):
        """创建测试用的 ClickHouse Writer"""
        writer = ClickHouseWriter(
            host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
            port=int(os.getenv('CLICKHOUSE_PORT', 9000)),
            database='stock_data',
            batch_size=100
        )
        yield writer
        writer.close()
    
    def test_connection(self, writer):
        """测试连接"""
        assert writer.client is not None
        result = writer.query("SELECT 1")
        assert result[0][0] == 1
    
    def test_write_single_snapshot(self, writer):
        """测试写入单条快照"""
        snapshot = SnapshotData(
            snapshot_time=datetime.now(),
            trade_date=datetime.now(),
            stock_code='000001',
            stock_name='平安银行',
            market='SZ',
            current_price=12.50,
            open_price=12.40,
            high_price=12.60,
            low_price=12.35,
            pre_close=12.45,
            # 买五档
            bid_price1=12.49, bid_volume1=100,
            bid_price2=12.48, bid_volume2=200,
            bid_price3=12.47, bid_volume3=150,
            bid_price4=12.46, bid_volume4=180,
            bid_price5=12.45, bid_volume5=220,
            # 卖五档
            ask_price1=12.50, ask_volume1=120,
            ask_price2=12.51, ask_volume2=210,
            ask_price3=12.52, ask_volume3=160,
            ask_price4=12.53, ask_volume4=190,
            ask_price5=12.54, ask_volume5=230,
            # 成交统计
            total_volume=1000000,
            total_amount=12500000.0,
            turnover_rate=0.5,
            pool_level='L1'
        )
        
        writer.write_snapshot(snapshot)
        writer.flush()
        
        # 验证数据
        result = writer.query(
            "SELECT count() FROM snapshot_data WHERE stock_code = '000001'"
        )
        assert result[0][0] >= 1
    
    def test_batch_write(self, writer):
        """测试批量写入"""
        snapshots = []
        for i in range(10):
            snapshot = SnapshotData(
                snapshot_time=datetime.now(),
                trade_date=datetime.now(),
                stock_code=f'00000{i % 5 + 1}',
                stock_name=f'测试股票{i}',
                market='SZ',
                current_price=10.0 + i * 0.1,
                bid_price1=10.0, bid_volume1=100,
                ask_price1=10.1, ask_volume1=100,
                total_volume=100000 * (i + 1),
                total_amount=1000000.0 * (i + 1),
                pool_level='L1'
            )
            snapshots.append(snapshot)
        
        writer.write_snapshots(snapshots)
        writer.flush()
        
        # 验证数据
        result = writer.query("SELECT count() FROM snapshot_data")
        assert result[0][0] >= 10
    
    def test_buffer_auto_flush(self, writer):
        """测试缓冲区自动提交"""
        # batch_size = 100，所以写入 100 条应该自动提交
        snapshots = []
        for i in range(100):
            snapshot = SnapshotData(
                snapshot_time=datetime.now(),
                trade_date=datetime.now(),
                stock_code='600000',
                stock_name='浦发银行',
                market='SH',
                current_price=8.0 + i * 0.01,
                bid_price1=8.0, bid_volume1=100,
                ask_price1=8.01, ask_volume1=100,
                total_volume=500000,
                total_amount=4000000.0,
                pool_level='L1'
            )
            snapshots.append(snapshot)
        
        writer.write_snapshots(snapshots)
        
        # 不手动 flush，应该已经自动提交
        assert len(writer._buffer) == 0
    
    def test_get_stats(self, writer):
        """测试获取统计信息"""
        stats = writer.get_stats()
        
        assert 'buffer_size' in stats
        assert 'batch_size' in stats
        assert 'host' in stats
        assert 'database' in stats
        assert stats['batch_size'] == 100


if __name__ == "__main__":
    pytest.main([__file__, '-v'])

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DualWriter 测试
验证双写协调器的功能
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, ANY
from src.core.storage.dual_writer import DualWriter
from src.core.storage.parquet_writer import ParquetWriter
from src.storage.clickhouse_writer import ClickHouseWriter

class TestDualWriter:
    """测试 DualWriter 类"""
    
    @pytest.fixture
    def mock_parquet(self):
        writer = MagicMock(spec=ParquetWriter)
        writer.save_snapshot.return_value = "/tmp/test.parquet"
        return writer
        
    @pytest.fixture
    def mock_clickhouse(self):
        writer = MagicMock(spec=ClickHouseWriter)
        return writer
        
    @pytest.fixture
    def dual_writer(self, mock_parquet, mock_clickhouse):
        return DualWriter(mock_parquet, mock_clickhouse)
        
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            'code': ['000001', '000002'],
            'price': [10.5, 11.2],
            'volume': [1000, 2000],
            'bid1': [10.4, 11.1],
            'bid_vol1': [100, 200],
            'ask1': [10.6, 11.3],
            'ask_vol1': [100, 200]
        })

    @pytest.mark.asyncio
    async def test_write_success(self, dual_writer, mock_parquet, mock_clickhouse, sample_df):
        """测试双写成功"""
        timestamp = datetime.now()
        
        p_success, c_success = await dual_writer.write(sample_df, timestamp)
        
        assert p_success is True
        assert c_success is True
        
        # 验证调用
        mock_parquet.save_snapshot.assert_called_once_with(sample_df, timestamp)
        mock_clickhouse.write_snapshots.assert_called_once()
        mock_clickhouse.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_parquet_failure(self, dual_writer, mock_parquet, mock_clickhouse, sample_df):
        """测试 Parquet 写入失败"""
        mock_parquet.save_snapshot.side_effect = Exception("Disk full")
        
        p_success, c_success = await dual_writer.write(sample_df)
        
        assert p_success is False
        assert c_success is True
        
        # ClickHouse 仍应成功
        mock_clickhouse.write_snapshots.assert_called_once()

    @pytest.mark.asyncio
    async def test_clickhouse_failure(self, dual_writer, mock_parquet, mock_clickhouse, sample_df):
        """测试 ClickHouse 写入失败"""
        mock_clickhouse.write_snapshots.side_effect = Exception("Connection lost")
        
        p_success, c_success = await dual_writer.write(sample_df)
        
        assert p_success is True
        assert c_success is False
        
        # Parquet 仍应成功
        mock_parquet.save_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_conversion(self, dual_writer, mock_clickhouse, sample_df):
        """测试 DataFrame 到 SnapshotData 的转换"""
        await dual_writer.write(sample_df)
        
        # 获取调用参数
        call_args = mock_clickhouse.write_snapshots.call_args
        snapshots = call_args[0][0]
        
        assert len(snapshots) == 2
        assert snapshots[0].stock_code == '000001'
        assert snapshots[0].current_price == 10.5
        assert snapshots[0].bid_price1 == 10.4

if __name__ == "__main__":
    pytest.main([__file__, '-v'])

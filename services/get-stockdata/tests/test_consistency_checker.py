#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ConsistencyChecker 测试
验证数据一致性校验功能
"""

import pytest
import pandas as pd
from datetime import date
from unittest.mock import MagicMock, AsyncMock
from src.core.consistency.consistency_checker import ConsistencyChecker
from src.storage.clickhouse_writer import ClickHouseWriter

class TestConsistencyChecker:
    """测试 ConsistencyChecker 类"""
    
    @pytest.fixture
    def temp_parquet_dir(self, tmp_path):
        """创建临时 Parquet 目录并写入数据"""
        base_dir = tmp_path / "snapshots"
        date_dir = base_dir / "2025-11-29" / "09"
        date_dir.mkdir(parents=True)
        
        # 创建两个 parquet 文件
        df1 = pd.DataFrame({'stock_code': ['000001'], 'total_volume': [1000]})
        df1.to_parquet(date_dir / "s1.parquet")
        
        df2 = pd.DataFrame({'stock_code': ['000002'], 'total_volume': [2000]})
        df2.to_parquet(date_dir / "s2.parquet")
        
        return base_dir
        
    @pytest.fixture
    def mock_clickhouse(self):
        writer = MagicMock(spec=ClickHouseWriter)
        return writer
        
    @pytest.fixture
    def checker(self, temp_parquet_dir, mock_clickhouse):
        return ConsistencyChecker(str(temp_parquet_dir), mock_clickhouse)

    @pytest.mark.asyncio
    async def test_check_consistent(self, checker, mock_clickhouse):
        """测试数据一致的情况"""
        # Mock ClickHouse 返回相同的数据
        # count=2, total_volume=3000
        mock_clickhouse.query.return_value = [(2, 3000)]
        
        check_date = date(2025, 11, 29)
        result = await checker.check_daily(check_date)
        
        assert result['consistent'] is True
        assert result['parquet']['count'] == 2
        assert result['clickhouse']['count'] == 2
        assert result['diff_count'] == 0

    @pytest.mark.asyncio
    async def test_check_inconsistent(self, checker, mock_clickhouse):
        """测试数据不一致的情况"""
        # Mock ClickHouse 返回不同的数据
        # count=1, total_volume=1000 (少了一条)
        mock_clickhouse.query.return_value = [(1, 1000)]
        
        check_date = date(2025, 11, 29)
        result = await checker.check_daily(check_date)
        
        assert result['consistent'] is False
        assert result['parquet']['count'] == 2
        assert result['clickhouse']['count'] == 1
        assert result['diff_count'] == 1

    @pytest.mark.asyncio
    async def test_no_data(self, checker, mock_clickhouse):
        """测试没有数据的情况"""
        mock_clickhouse.query.return_value = [(0, 0)]
        
        # 检查一个不存在的日期
        check_date = date(2025, 1, 1)
        result = await checker.check_daily(check_date)
        
        assert result['consistent'] is True
        assert result['parquet']['count'] == 0
        assert result['clickhouse']['count'] == 0

if __name__ == "__main__":
    pytest.main([__file__, '-v'])

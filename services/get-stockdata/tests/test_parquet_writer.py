#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parquet Writer 测试
验证 Parquet 文件写入、分片、压缩和清理功能
"""

import pytest
import pandas as pd
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from src.core.storage.parquet_writer import ParquetWriter


class TestParquetWriter:
    """测试 ParquetWriter 类"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """创建临时目录"""
        return tmp_path / "parquet_data"
        
    @pytest.fixture
    def writer(self, temp_dir):
        """创建测试用的 Parquet Writer"""
        return ParquetWriter(str(temp_dir), retention_days=7)
        
    @pytest.fixture
    def sample_df(self):
        """创建测试数据"""
        return pd.DataFrame({
            'stock_code': ['000001', '000002', '600000'],
            'price': [10.5, 11.2, 8.8],
            'volume': [1000, 2000, 1500]
        })

    def test_save_snapshot_structure(self, writer, temp_dir, sample_df):
        """测试目录结构生成"""
        timestamp = datetime(2025, 11, 29, 9, 30, 0)
        file_path = writer.save_snapshot(sample_df, timestamp)
        
        # 验证路径: base/2025-11-29/09/snapshot_20251129_093000.parquet
        expected_dir = temp_dir / "2025-11-29" / "09"
        assert expected_dir.exists()
        assert Path(file_path).exists()
        assert "snapshot_20251129_093000.parquet" in file_path
        
    def test_compression(self, writer, sample_df):
        """验证是否使用了 snappy 压缩"""
        # 注意：直接验证压缩算法比较困难，我们验证文件可以被读取且大小合理
        timestamp = datetime.now()
        file_path = writer.save_snapshot(sample_df, timestamp)
        
        # 读取验证
        df_read = pd.read_parquet(file_path)
        assert len(df_read) == 3
        assert 'stock_code' in df_read.columns
        
        # 验证元数据（如果可能）
        # pyarrow.parquet.read_metadata(file_path) 可以查看压缩信息
        import pyarrow.parquet as pq
        metadata = pq.read_metadata(file_path)
        # 检查第一列的压缩算法
        row_group = metadata.row_group(0)
        column = row_group.column(0)
        # 可能是 SNAPPY 或 GZIP，取决于实现。我们期望 SNAPPY
        assert column.compression == 'SNAPPY'

    def test_cleanup_old_files(self, writer, temp_dir, sample_df):
        """测试过期文件清理"""
        # 创建一个 8 天前的文件
        old_date = datetime.now() - timedelta(days=8)
        old_path = writer.save_snapshot(sample_df, old_date)
        
        # 创建一个今天的文件
        current_path = writer.save_snapshot(sample_df, datetime.now())
        
        assert Path(old_path).exists()
        assert Path(current_path).exists()
        
        # 执行清理
        writer.cleanup_old_files()
        
        # 验证
        assert not Path(old_path).exists()  # 应该被删除
        assert Path(current_path).exists()  # 应该保留
        
        # 验证日期目录是否被删除
        old_date_dir = Path(old_path).parent.parent
        assert not old_date_dir.exists()

    def test_metadata_file(self, writer, temp_dir, sample_df):
        """测试元数据记录（可选）"""
        # 如果实现了元数据记录功能
        pass

if __name__ == "__main__":
    pytest.main([__file__, '-v'])

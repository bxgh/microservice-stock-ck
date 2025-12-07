import asyncio
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, Optional

from src.core.storage.parquet_writer import ParquetWriter
from src.storage.clickhouse_writer import ClickHouseWriter

logger = logging.getLogger(__name__)

class ConsistencyChecker:
    """
    数据一致性校验器
    对比 Parquet 归档数据和 ClickHouse 实时数据的一致性
    """
    
    def __init__(self, parquet_path: str, clickhouse_writer: ClickHouseWriter):
        self.parquet_path = Path(parquet_path)
        self.clickhouse = clickhouse_writer
        
    async def check_daily(self, check_date: date) -> Dict[str, Any]:
        """
        检查某一天的数据一致性
        
        Args:
            check_date: 检查日期
            
        Returns:
            校验结果字典
        """
        logger.info(f"🔍 Starting consistency check for {check_date}")
        
        # 1. 统计 Parquet 数据
        parquet_stats = await self._count_parquet(check_date)
        
        # 2. 统计 ClickHouse 数据
        clickhouse_stats = await self._count_clickhouse(check_date)
        
        # 3. 对比结果
        is_consistent = (
            parquet_stats['count'] == clickhouse_stats['count'] and
            abs(parquet_stats['total_volume'] - clickhouse_stats['total_volume']) < 1  # 允许微小误差
        )
        
        result = {
            'date': check_date.isoformat(),
            'consistent': is_consistent,
            'parquet': parquet_stats,
            'clickhouse': clickhouse_stats,
            'diff_count': parquet_stats['count'] - clickhouse_stats['count']
        }
        
        if not is_consistent:
            logger.warning(f"⚠️ Inconsistency detected for {check_date}: {result}")
        else:
            logger.info(f"✅ Data consistent for {check_date}")
            
        return result

    async def _count_parquet(self, check_date: date) -> Dict[str, Any]:
        """统计 Parquet 文件中的数据量"""
        date_str = check_date.strftime('%Y-%m-%d')
        date_dir = self.parquet_path / date_str
        
        total_count = 0
        total_volume = 0
        
        if not date_dir.exists():
            # 尝试旧格式
            date_str_old = check_date.strftime('%Y%m%d')
            date_dir = self.parquet_path / date_str_old
            if not date_dir.exists():
                return {'count': 0, 'total_volume': 0}
        
        # 遍历所有 parquet 文件
        # 这可能比较慢，但在后台任务中可以接受
        files = list(date_dir.rglob("*.parquet"))
        
        for f in files:
            try:
                # 只读取需要的列以加速
                df = pd.read_parquet(f, columns=['total_volume'])
                total_count += len(df)
                total_volume += df['total_volume'].sum()
            except Exception as e:
                logger.error(f"Failed to read parquet {f}: {e}")
                
        return {
            'count': total_count,
            'total_volume': int(total_volume)
        }

    async def _count_clickhouse(self, check_date: date) -> Dict[str, Any]:
        """统计 ClickHouse 中的数据量"""
        date_str = check_date.strftime('%Y-%m-%d')
        
        sql = f"""
        SELECT 
            count(), 
            sum(total_volume) 
        FROM snapshot_data 
        WHERE toDate(trade_date) = '{date_str}'
        """
        
        try:
            result = self.clickhouse.query(sql)
            if result and result[0]:
                return {
                    'count': result[0][0],
                    'total_volume': int(result[0][1] or 0)
                }
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            
        return {'count': 0, 'total_volume': 0}

    async def repair(self, check_date: date):
        """
        修复数据（从 Parquet 回填到 ClickHouse）
        注意：这是一个昂贵的操作
        """
        # TODO: 实现修复逻辑
        # 1. 读取 Parquet
        # 2. 写入 ClickHouse (使用 INSERT IGNORE 或 ReplacingMergeTree 自动去重)
        pass

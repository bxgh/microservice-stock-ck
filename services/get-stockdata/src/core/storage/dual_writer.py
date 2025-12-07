import asyncio
import logging
import pandas as pd
from datetime import datetime
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from src.core.storage.parquet_writer import ParquetWriter
from src.storage.clickhouse_writer import ClickHouseWriter, SnapshotData

logger = logging.getLogger(__name__)

class DualWriter:
    """
    双写存储协调器
    协调 Parquet (归档) 和 ClickHouse (实时) 的写入操作
    """
    
    def __init__(self, parquet_writer: ParquetWriter, clickhouse_writer: ClickHouseWriter):
        self.parquet = parquet_writer
        self.clickhouse = clickhouse_writer
        self._executor = ThreadPoolExecutor(max_workers=2)  # 两个写入任务并行
        
    async def write(self, df: pd.DataFrame, timestamp: Optional[datetime] = None) -> Tuple[bool, bool]:
        """
        执行双写操作
        
        Args:
            df: 快照数据 DataFrame
            timestamp: 时间戳
            
        Returns:
            (parquet_success, clickhouse_success): 写入结果元组
        """
        if df is None or df.empty:
            return True, True
            
        if timestamp is None:
            timestamp = datetime.now()
            
        # 并行执行写入任务
        loop = asyncio.get_running_loop()
        
        # 1. Parquet 写入任务
        parquet_task = loop.run_in_executor(
            self._executor, 
            self._write_parquet, 
            df, 
            timestamp
        )
        
        # 2. ClickHouse 写入任务
        clickhouse_task = loop.run_in_executor(
            self._executor,
            self._write_clickhouse,
            df,
            timestamp
        )
        
        # 等待所有任务完成
        results = await asyncio.gather(parquet_task, clickhouse_task, return_exceptions=True)
        
        parquet_result = results[0]
        clickhouse_result = results[1]
        
        # 处理结果
        p_success = isinstance(parquet_result, bool) and parquet_result
        c_success = isinstance(clickhouse_result, bool) and clickhouse_result
        
        if not p_success:
            logger.error(f"❌ Parquet write failed: {parquet_result}")
            
        if not c_success:
            logger.error(f"❌ ClickHouse write failed: {clickhouse_result}")
            
        return p_success, c_success

    def _write_parquet(self, df: pd.DataFrame, timestamp: datetime) -> bool:
        """Parquet 写入包装"""
        try:
            path = self.parquet.save_snapshot(df, timestamp)
            return bool(path)
        except Exception as e:
            logger.error(f"Parquet write exception: {e}")
            raise e

    def _write_clickhouse(self, df: pd.DataFrame, timestamp: datetime) -> bool:
        """ClickHouse 写入包装"""
        try:
            # 转换 DataFrame 到 SnapshotData 列表
            snapshots = self._df_to_snapshots(df, timestamp)
            
            # 写入
            self.clickhouse.write_snapshots(snapshots)
            # 强制刷新以确保写入（或者依赖自动刷新，但为了事务性最好手动刷新）
            self.clickhouse.flush()
            return True
        except Exception as e:
            logger.error(f"ClickHouse write exception: {e}")
            raise e

    def _df_to_snapshots(self, df: pd.DataFrame, timestamp: datetime) -> List[SnapshotData]:
        """将 DataFrame 转换为 SnapshotData 对象列表"""
        snapshots = []
        # 确保 timestamp 是 datetime 对象
        ts = timestamp
        date = ts.date()
        
        # 遍历 DataFrame 行
        # 注意：itertuples 比 iterrows 快
        for row in df.itertuples(index=False):
            # 动态获取属性，处理可能缺失的字段
            def get_val(name, default=0):
                return getattr(row, name, default)
            
            # 假设 DataFrame 列名已经标准化（这需要在采集层保证，或者在这里做映射）
            # 这里假设列名与 SnapshotData 字段名一致或有对应关系
            # 实际 Mootdx 返回的列名可能不同，需要映射
            
            # 简单的列名映射逻辑 (根据 Mootdx 返回结构调整)
            # Mootdx: code, price, ...
            
            try:
                snapshot = SnapshotData(
                    snapshot_time=ts,
                    trade_date=date,
                    stock_code=str(get_val('code')),
                    stock_name=str(get_val('name', '')), # Mootdx quotes 可能不返回 name
                    market=self._map_market(str(get_val('market', 'SZ'))), # 映射 0/1 到 SZ/SH
                    current_price=float(get_val('price', 0)),
                    open_price=float(get_val('open', 0)),
                    high_price=float(get_val('high', 0)),
                    low_price=float(get_val('low', 0)),
                    pre_close=float(get_val('last_close', 0)),
                    
                    # 买五
                    bid_price1=float(get_val('bid1', 0)), bid_volume1=int(get_val('bid_vol1', 0)),
                    bid_price2=float(get_val('bid2', 0)), bid_volume2=int(get_val('bid_vol2', 0)),
                    bid_price3=float(get_val('bid3', 0)), bid_volume3=int(get_val('bid_vol3', 0)),
                    bid_price4=float(get_val('bid4', 0)), bid_volume4=int(get_val('bid_vol4', 0)),
                    bid_price5=float(get_val('bid5', 0)), bid_volume5=int(get_val('bid_vol5', 0)),
                    
                    # 卖五
                    ask_price1=float(get_val('ask1', 0)), ask_volume1=int(get_val('ask_vol1', 0)),
                    ask_price2=float(get_val('ask2', 0)), ask_volume2=int(get_val('ask_vol2', 0)),
                    ask_price3=float(get_val('ask3', 0)), ask_volume3=int(get_val('ask_vol3', 0)),
                    ask_price4=float(get_val('ask4', 0)), ask_volume4=int(get_val('ask_vol4', 0)),
                    ask_price5=float(get_val('ask5', 0)), ask_volume5=int(get_val('ask_vol5', 0)),
                    
                    total_volume=int(get_val('volume', 0)),
                    total_amount=float(get_val('amount', 0)),
                    # turnover_rate=float(get_val('turnover', 0)) # Mootdx 可能不返回
                )
                snapshots.append(snapshot)
            except Exception as e:
                logger.warning(f"Failed to convert row to SnapshotData: {e}, Row: {row}")
                continue
                
        return snapshots

    def _map_market(self, raw_market: str) -> str:
        """映射市场代码"""
        if raw_market == '0':
            return 'SZ'
        elif raw_market == '1':
            return 'SH'
        return raw_market

    def close(self):
        """关闭资源"""
        self._executor.shutdown(wait=True)
        self.clickhouse.close()

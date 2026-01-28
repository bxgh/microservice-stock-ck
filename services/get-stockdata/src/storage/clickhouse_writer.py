from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import List, Optional
import logging
from clickhouse_driver import Client

logger = logging.getLogger(__name__)

@dataclass
class SnapshotData:
    """快照数据模型"""
    snapshot_time: datetime
    trade_date: date
    stock_code: str
    stock_name: str
    market: str
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    pre_close: float
    bid_price1: float
    bid_volume1: int
    bid_price2: float
    bid_volume2: int
    bid_price3: float
    bid_volume3: int
    bid_price4: float
    bid_volume4: int
    bid_price5: float
    bid_volume5: int
    ask_price1: float
    ask_volume1: int
    ask_price2: float
    ask_volume2: int
    ask_price3: float
    ask_volume3: int
    ask_price4: float
    ask_volume4: int
    ask_price5: float
    ask_volume5: int
    total_volume: int
    total_amount: float
    turnover_rate: float = 0.0
    data_source: str = 'mootdx'
    pool_level: str = 'L1'
    created_at: Optional[datetime] = None

class ClickHouseWriter:
    """ClickHouse 数据写入器 (同步版，供 DualWriter ThreadPool 使用)"""
    
    def __init__(self, host: str, port: int, database: str, user: str = 'default', password: str = '', table_name: str = 'snapshot_data'):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.table_name = table_name
        self.client = None
        self._connect()
        
    def _connect(self):
        """建立数据库连接，包含重试逻辑"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.client = Client(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    settings={'use_numpy': False, 'connect_timeout': 10}
                )
                # 测试连接
                self.client.execute('SELECT 1')
                logger.info(f"✅ ClickHouseWriter connected to {self.host}:{self.port}/{self.database}")
                return
            except Exception as e:
                logger.error(f"❌ ClickHouseWriter connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                else:
                    raise ConnectionError(f"Failed to connect to ClickHouse after {max_retries} attempts")

    def write_snapshots(self, snapshots: List[SnapshotData]):
        """批量写入快照数据"""
        if not snapshots:
            return
            
        try:
            # 转换为字典列表
            data = [asdict(s) for s in snapshots]
            
            # 执行插入，明确指定字段以避开 created_at (由 CK 自动填充)
            table = self.table_name
            columns = [
                "snapshot_time", "trade_date", "stock_code", "stock_name", "market",
                "current_price", "open_price", "high_price", "low_price", "pre_close",
                "bid_price1", "bid_volume1", "bid_price2", "bid_volume2",
                "bid_price3", "bid_volume3", "bid_price4", "bid_volume4",
                "bid_price5", "bid_volume5", "ask_price1", "ask_volume1",
                "ask_price2", "ask_volume2", "ask_price3", "ask_volume3",
                "ask_price4", "ask_volume4", "ask_price5", "ask_volume5",
                "total_volume", "total_amount", "turnover_rate", "data_source", "pool_level", "created_at"
            ]
            column_str = ", ".join(columns)
            self.client.execute(
                f'INSERT INTO {table} ({column_str}) VALUES',
                data
            )
            # logger.debug(f"Inserted {len(snapshots)} snapshots to ClickHouse")
        except Exception as e:
            logger.error(f"❌ ClickHouse write error: {e}")
            # 尝试重连
            self._connect()
            raise

    def flush(self):
        """刷新缓冲区（clickhouse-driver insert values 是立即执行的）"""
        pass

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.disconnect()
            self.client = None

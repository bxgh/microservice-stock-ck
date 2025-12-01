#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ClickHouse 写入器
用于将盘口快照数据批量写入 ClickHouse 数据库
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError

logger = logging.getLogger(__name__)


class SnapshotData:
    """盘口快照数据模型"""
    
    def __init__(
        self,
        snapshot_time: datetime,
        trade_date: datetime,
        stock_code: str,
        stock_name: str,
        market: str,
        current_price: float,
        open_price: float = 0.0,
        high_price: float = 0.0,
        low_price: float = 0.0,
        pre_close: float = 0.0,
        # 买五档
        bid_price1: float = 0.0, bid_volume1: int = 0,
        bid_price2: float = 0.0, bid_volume2: int = 0,
        bid_price3: float = 0.0, bid_volume3: int = 0,
        bid_price4: float = 0.0, bid_volume4: int = 0,
        bid_price5: float = 0.0, bid_volume5: int = 0,
        # 卖五档
        ask_price1: float = 0.0, ask_volume1: int = 0,
        ask_price2: float = 0.0, ask_volume2: int = 0,
        ask_price3: float = 0.0, ask_volume3: int = 0,
        ask_price4: float = 0.0, ask_volume4: int = 0,
        ask_price5: float = 0.0, ask_volume5: int = 0,
        # 成交统计
        total_volume: int = 0,
        total_amount: float = 0.0,
        turnover_rate: float = 0.0,
        # 元数据
        data_source: str = 'mootdx',
        pool_level: str = 'L1'
    ):
        self.snapshot_time = snapshot_time
        self.trade_date = trade_date.date() if isinstance(trade_date, datetime) else trade_date
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.market = market
        self.current_price = current_price
        self.open_price = open_price
        self.high_price = high_price
        self.low_price = low_price
        self.pre_close = pre_close
        
        # 买五档
        self.bid_price1 = bid_price1
        self.bid_volume1 = bid_volume1
        self.bid_price2 = bid_price2
        self.bid_volume2 = bid_volume2
        self.bid_price3 = bid_price3
        self.bid_volume3 = bid_volume3
        self.bid_price4 = bid_price4
        self.bid_volume4 = bid_volume4
        self.bid_price5 = bid_price5
        self.bid_volume5 = bid_volume5
        
        # 卖五档
        self.ask_price1 = ask_price1
        self.ask_volume1 = ask_volume1
        self.ask_price2 = ask_price2
        self.ask_volume2 = ask_volume2
        self.ask_price3 = ask_price3
        self.ask_volume3 = ask_volume3
        self.ask_price4 = ask_price4
        self.ask_volume4 = ask_volume4
        self.ask_price5 = ask_price5
        self.ask_volume5 = ask_volume5
        
        # 成交统计
        self.total_volume = total_volume
        self.total_amount = total_amount
        self.turnover_rate = turnover_rate
        
        # 元数据
        self.data_source = data_source
        self.pool_level = pool_level


class ClickHouseWriter:
    """
    ClickHouse 数据写入器
    
    特性：
    - 批量写入优化
    - 自动重连机制
    - 错误处理和日志
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 9000,
        database: str = 'stock_data',
        user: str = 'default',
        password: str = '',
        batch_size: int = 5000
    ):
        """
        初始化 ClickHouse 写入器
        
        Args:
            host: ClickHouse 主机地址
            port: TCP 端口（默认 9000）
            database: 数据库名
            user: 用户名
            password: 密码
            batch_size: 批量写入大小
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.batch_size = batch_size
        
        self.client: Optional[Client] = None
        self._buffer: List[SnapshotData] = []
        self._init_client()
        
    def _init_client(self):
        """初始化 ClickHouse 客户端"""
        try:
            self.client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                settings={'use_numpy': False}
            )
            logger.info(f"✅ ClickHouse 客户端已连接: {self.host}:{self.port}/{self.database}")
        except ClickHouseError as e:
            logger.error(f"❌ ClickHouse 连接失败: {e}")
            raise
            
    def write_snapshot(self, snapshot: SnapshotData):
        """
        写入单条快照数据（异步缓冲）
        
        Args:
            snapshot: 快照数据对象
        """
        self._buffer.append(snapshot)
        
        if len(self._buffer) >= self.batch_size:
            self.flush()
            
    def write_snapshots(self, snapshots: List[SnapshotData]):
        """
        批量写入快照数据
        
        Args:
            snapshots: 快照数据列表
        """
        self._buffer.extend(snapshots)
        
        if len(self._buffer) >= self.batch_size:
            self.flush()
            
    def flush(self):
        """强制提交缓冲区数据"""
        if not self._buffer:
            return
            
        try:
            # 准备数据
            data = [self._to_row(snapshot) for snapshot in self._buffer]
            
            # 批量插入（明确指定列名，跳过 created_at 使用默认值）
            self.client.execute(
                '''INSERT INTO snapshot_data (
                    snapshot_time, trade_date, stock_code, stock_name, market,
                    current_price, open_price, high_price, low_price, pre_close,
                    bid_price1, bid_volume1, bid_price2, bid_volume2, bid_price3, bid_volume3,
                    bid_price4, bid_volume4, bid_price5, bid_volume5,
                    ask_price1, ask_volume1, ask_price2, ask_volume2, ask_price3, ask_volume3,
                    ask_price4, ask_volume4, ask_price5, ask_volume5,
                    total_volume, total_amount, turnover_rate,
                    data_source, pool_level
                ) VALUES''',
                data
            )
            
            logger.info(f"✅ 写入 {len(self._buffer)} 条快照数据到 ClickHouse")
            self._buffer.clear()
            
        except ClickHouseError as e:
            logger.error(f"❌ ClickHouse 写入失败: {e}")
            # 可以选择重试或记录失败数据
            raise
            
    def _to_row(self, snapshot: SnapshotData) -> tuple:
        """将 SnapshotData 对象转换为元组（匹配表结构）"""
        return (
            snapshot.snapshot_time,
            snapshot.trade_date,
            snapshot.stock_code,
            snapshot.stock_name,
            snapshot.market,
            snapshot.current_price,
            snapshot.open_price,
            snapshot.high_price,
            snapshot.low_price,
            snapshot.pre_close,
            # 买五档
            snapshot.bid_price1, snapshot.bid_volume1,
            snapshot.bid_price2, snapshot.bid_volume2,
            snapshot.bid_price3, snapshot.bid_volume3,
            snapshot.bid_price4, snapshot.bid_volume4,
            snapshot.bid_price5, snapshot.bid_volume5,
            # 卖五档
            snapshot.ask_price1, snapshot.ask_volume1,
            snapshot.ask_price2, snapshot.ask_volume2,
            snapshot.ask_price3, snapshot.ask_volume3,
            snapshot.ask_price4, snapshot.ask_volume4,
            snapshot.ask_price5, snapshot.ask_volume5,
            # 成交统计
            snapshot.total_volume,
            snapshot.total_amount,
            snapshot.turnover_rate,
            # 元数据
            snapshot.data_source,
            snapshot.pool_level
        )
        
    def query(self, sql: str) -> List[tuple]:
        """
        执行查询
        
        Args:
            sql: SQL 查询语句
            
        Returns:
            查询结果列表
        """
        try:
            result = self.client.execute(sql)
            return result
        except ClickHouseError as e:
            logger.error(f"❌ ClickHouse 查询失败: {e}")
            raise
            
    def get_stats(self) -> Dict[str, Any]:
        """获取写入统计信息"""
        return {
            'buffer_size': len(self._buffer),
            'batch_size': self.batch_size,
            'host': self.host,
            'database': self.database
        }
        
    def close(self):
        """关闭连接"""
        if self._buffer:
            self.flush()  # 提交剩余数据
            
        if self.client:
            self.client.disconnect()
            logger.info("ClickHouse 客户端已断开")


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建写入器
    writer = ClickHouseWriter(
        host='localhost',
        port=9000,
        database='stock_data',
        batch_size=1000
    )
    
    # 创建测试数据
    test_snapshot = SnapshotData(
        snapshot_time=datetime.now(),
        trade_date=datetime.now(),
        stock_code='000001',
        stock_name='平安银行',
        market='SZ',
        current_price=12.50,
        bid_price1=12.49, bid_volume1=100,
        ask_price1=12.50, ask_volume1=200,
        total_volume=1000000,
        total_amount=12500000.0,
        pool_level='L1'
    )
    
    # 写入数据
    writer.write_snapshot(test_snapshot)
    writer.flush()
    
    # 查询验证
    result = writer.query("SELECT count() FROM snapshot_data")
    print(f"总记录数: {result[0][0]}")
    
    # 关闭连接
    writer.close()

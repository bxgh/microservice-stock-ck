#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ClickHouse 写入器
用于将盘口快照数据批量写入 ClickHouse 数据库
"""

import logging
import asyncio
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


class FinancialIndicatorData:
    """财务指标数据模型"""
    def __init__(self, stock_code: str, report_date: datetime, report_type: str, **kwargs):
        self.stock_code = stock_code
        self.report_date = report_date.date() if isinstance(report_date, datetime) else report_date
        self.report_type = report_type
        self.revenue = kwargs.get('revenue', 0.0)
        self.operating_cost = kwargs.get('operating_cost', 0.0)
        self.operating_profit = kwargs.get('operating_profit', 0.0)
        self.net_profit = kwargs.get('net_profit', 0.0)
        self.total_assets = kwargs.get('total_assets', 0.0)
        self.net_assets = kwargs.get('net_assets', 0.0)
        self.goodwill = kwargs.get('goodwill', 0.0)
        self.monetary_funds = kwargs.get('monetary_funds', 0.0)
        self.interest_bearing_debt = kwargs.get('interest_bearing_debt', 0.0)
        self.accounts_receivable = kwargs.get('accounts_receivable', 0.0)
        self.inventory = kwargs.get('inventory', 0.0)
        self.accounts_payable = kwargs.get('accounts_payable', 0.0)
        self.operating_cash_flow = kwargs.get('operating_cash_flow', 0.0)
        self.major_shareholder_pledge_ratio = kwargs.get('major_shareholder_pledge_ratio', 0.0)
        self.data_source = kwargs.get('data_source', 'akshare')


class ValuationData:
    """估值数据模型"""
    def __init__(self, stock_code: str, trade_date: datetime, **kwargs):
        self.stock_code = stock_code
        self.trade_date = trade_date.date() if isinstance(trade_date, datetime) else trade_date
        self.total_market_cap = kwargs.get('total_market_cap', 0.0)
        self.circulating_market_cap = kwargs.get('circulating_market_cap', 0.0)
        self.pe_ttm = kwargs.get('pe_ttm', 0.0)
        self.pe_static = kwargs.get('pe_static', 0.0)
        self.pb_ratio = kwargs.get('pb_ratio', 0.0)
        self.ps_ratio = kwargs.get('ps_ratio', 0.0)
        self.pcf_ratio = kwargs.get('pcf_ratio', 0.0)
        self.dividend_yield_ttm = kwargs.get('dividend_yield_ttm', 0.0)
        self.data_source = kwargs.get('data_source', 'akshare')


class IndustryInfoData:
    """行业信息数据模型"""
    def __init__(self, stock_code: str, industry: str, sector: str, list_date: Optional[datetime] = None, **kwargs):
        self.stock_code = stock_code
        self.industry = industry
        self.sector = sector
        self.list_date = list_date.date() if isinstance(list_date, datetime) else list_date
        self.total_shares = kwargs.get('total_shares', 0)
        self.data_source = kwargs.get('data_source', 'akshare')
        self.updated_at = datetime.now()


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
        self._snapshot_buffer: List[SnapshotData] = []
        self._finance_buffer: List[FinancialIndicatorData] = []
        self._valuation_buffer: List[ValuationData] = []
        self._industry_buffer: List[IndustryInfoData] = []
        self._lock = asyncio.Lock()
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
            
    async def write_snapshot(self, snapshot: SnapshotData):
        """写入单条快照数据"""
        async with self._lock:
            self._snapshot_buffer.append(snapshot)
            if len(self._snapshot_buffer) >= self.batch_size:
                await self.flush_snapshots()
            
    async def write_snapshots(self, snapshots: List[SnapshotData]):
        """批量写入快照数据"""
        async with self._lock:
            self._snapshot_buffer.extend(snapshots)
            if len(self._snapshot_buffer) >= self.batch_size:
                await self.flush_snapshots()

    async def write_financial_indicators(self, data: List[FinancialIndicatorData]):
        """批量写入财务指标"""
        logger.debug(f"write_financial_indicators called with {len(data)} items")
        async with self._lock:
            self._finance_buffer.extend(data)
            logger.debug(f"Finance buffer size: {len(self._finance_buffer)}, batch_size: {self.batch_size}")
            if len(self._finance_buffer) >= self.batch_size:
                await self.flush_finance()

    async def write_valuation(self, data: List[ValuationData]):
        """批量写入估值数据"""
        logger.debug(f"write_valuation called with {len(data)} items")
        async with self._lock:
            self._valuation_buffer.extend(data)
            logger.debug(f"Valuation buffer size: {len(self._valuation_buffer)}, batch_size: {self.batch_size}")
            if len(self._valuation_buffer) >= self.batch_size:
                await self.flush_valuation()

    async def write_industry_info(self, data: List[IndustryInfoData]):
        """批量写入行业信息"""
        logger.debug(f"write_industry_info called with {len(data)} items")
        async with self._lock:
            self._industry_buffer.extend(data)
            logger.debug(f"Industry buffer size: {len(self._industry_buffer)}, batch_size: {self.batch_size}")
            if len(self._industry_buffer) >= self.batch_size:
                await self.flush_industry()

    async def flush(self):
        """提交所有缓冲区数据"""
        async with self._lock:
            await self.flush_snapshots()
            await self.flush_finance()
            await self.flush_valuation()
            await self.flush_industry()

    async def flush_snapshots(self):
        if not self._snapshot_buffer:
            return
        try:
            data = [self._to_row(s) for s in self._snapshot_buffer]
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
            logger.info(f"✅ 成功写入 {items_count} 条快照到 ClickHouse")
            self._snapshot_buffer.clear()
        except ClickHouseError as e:
            logger.error(f"❌ ClickHouse Snapshot 写入失败 (Table: snapshot_data): {e}")
            raise

    async def flush_finance(self):
        # 假设调用此方法时已经持有 self._lock
        if not self._finance_buffer:
            return
        try:
            items_count = len(self._finance_buffer)
            data = [
                (
                    f.stock_code, f.report_date, f.report_type,
                    f.revenue, f.operating_cost, f.operating_profit, f.net_profit,
                    f.total_assets, f.net_assets, f.goodwill, f.monetary_funds,
                    f.interest_bearing_debt, f.accounts_receivable, f.inventory, f.accounts_payable,
                    f.operating_cash_flow, f.major_shareholder_pledge_ratio,
                    f.data_source
                ) for f in self._finance_buffer
            ]
            self.client.execute(
                '''INSERT INTO financial_indicators (
                    stock_code, report_date, report_type,
                    revenue, operating_cost, operating_profit, net_profit,
                    total_assets, net_assets, goodwill, monetary_funds,
                    interest_bearing_debt, accounts_receivable, inventory, accounts_payable,
                    operating_cash_flow, major_shareholder_pledge_ratio,
                    data_source
                ) VALUES''',
                data
            )
            logger.info(f"✅ 成功写入 {items_count} 条财务指标到 ClickHouse")
            self._finance_buffer.clear()
        except ClickHouseError as e:
            logger.error(f"❌ ClickHouse Finance 写入失败 (Table: financial_indicators): {e}")
            raise

    async def flush_valuation(self):
        # 假设调用此方法时已经持有 self._lock
        if not self._valuation_buffer:
            return
        try:
            items_count = len(self._valuation_buffer)
            data = [
                (
                    v.stock_code, v.trade_date,
                    v.total_market_cap, v.circulating_market_cap,
                    v.pe_ttm, v.pe_static, v.pb_ratio, v.ps_ratio, v.pcf_ratio, v.dividend_yield_ttm,
                    v.data_source
                ) for v in self._valuation_buffer
            ]
            self.client.execute(
                '''INSERT INTO valuation_data (
                    stock_code, trade_date,
                    total_market_cap, circulating_market_cap,
                    pe_ttm, pe_static, pb_ratio, ps_ratio, pcf_ratio, dividend_yield_ttm,
                    data_source
                ) VALUES''',
                data
            )
            logger.info(f"✅ 成功写入 {items_count} 条估值数据到 ClickHouse")
            self._valuation_buffer.clear()
        except ClickHouseError as e:
            logger.error(f"❌ ClickHouse Valuation 写入失败 (Table: valuation_data): {e}")
            raise

    async def flush_industry(self):
        # 假设调用此方法时已经持有 self._lock
        if not self._industry_buffer:
            return
        try:
            items_count = len(self._industry_buffer)
            data = [
                (
                    i.stock_code, i.industry, i.sector, i.list_date, i.total_shares,
                    i.data_source, i.updated_at
                ) for i in self._industry_buffer
            ]
            self.client.execute(
                '''INSERT INTO industry_info (
                    stock_code, industry, sector, list_date, total_shares,
                    data_source, updated_at
                ) VALUES''',
                data
            )
            logger.info(f"✅ 成功写入 {items_count} 条行业信息到 ClickHouse")
            self._industry_buffer.clear()
        except ClickHouseError as e:
            logger.error(f"❌ ClickHouse Industry 写入失败 (Table: industry_info): {e}")
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
            # 查询操作通常是只读的，不涉及缓冲区修改，因此不需要锁
            # 但如果客户端连接本身可能被其他线程/协程断开或重新初始化，则需要保护
            # 考虑到_init_client只在初始化时调用，close在结束时调用，这里暂时不加锁
            result = self.client.execute(sql)
            return result
        except ClickHouseError as e:
            logger.error(f"❌ ClickHouse 查询失败: {e}")
            raise
            
    def get_stats(self) -> Dict[str, Any]:
        """获取写入统计信息"""
        # 读取缓冲区长度是原子操作，不需要锁
        return {
            'snapshot_buffer': len(self._snapshot_buffer),
            'finance_buffer': len(self._finance_buffer),
            'valuation_buffer': len(self._valuation_buffer),
            'industry_buffer': len(self._industry_buffer),
            'batch_size': self.batch_size,
            'host': self.host,
            'database': self.database
        }
        
    def close(self):
        """关闭客户端"""
        # 在非异步上下文（如程序退出）中调用 flush() 需要特殊处理
        # 理想情况下，应该在异步事件循环中调用 await self.flush()
        # 这里为了兼容同步调用，尝试执行 flush，但可能无法完全刷新所有数据
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，可以尝试调度 flush
                # 但在 close 方法中通常不建议阻塞等待，所以这里只是一个提示
                logger.warning("ClickHouseWriter.close() called in running event loop. Consider awaiting self.flush() explicitly.")
                # asyncio.create_task(self.flush()) # 不等待结果，可能导致数据丢失
            else:
                # 如果没有运行的事件循环，创建一个新的并运行 flush
                # 这在某些情况下可能导致问题，但对于简单的清理是可行的
                logger.debug("Running flush in a new event loop for ClickHouseWriter.close()")
                loop.run_until_complete(self.flush())
        except RuntimeError:
            # No running event loop, and cannot create a new one (e.g., in a thread)
            logger.warning("ClickHouseWriter.close() called without an active event loop. Buffers might not be flushed.")
        except Exception as e:
            logger.error(f"Error during flush in ClickHouseWriter.close(): {e}")

        if self.client:
            try:
                self.client.disconnect()
                logger.info("ClickHouse 客户端已断开")
            except Exception as e:
                logger.error(f"ClickHouse 关闭异常: {e}")
            self.client = None




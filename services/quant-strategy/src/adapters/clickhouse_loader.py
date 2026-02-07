
"""
ClickHouse 数据加载适配器
负责高效加载分笔数据(Ticks)和快照数据(Snapshots)
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from clickhouse_driver import Client

from adapters.data_utils import DataValidator
from config.settings import settings

logger = logging.getLogger(__name__)

class ClickHouseLoader:
    def __init__(self):
        self.client = None
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=10) # 限制并发线程数

        self.snapshot_table = "snapshot_data_distributed"
        self.tick_table_history = "tick_data"
        self.tick_table_intraday = "tick_data_intraday"

    async def initialize(self):
        """异步初始化连接"""
        async with self._lock:
            if self.client is None:
                self.client = Client(
                    host=settings.QS_CLICKHOUSE_HOST,
                    port=settings.QS_CLICKHOUSE_PORT,
                    user=settings.QS_CLICKHOUSE_USER,
                    password=settings.QS_CLICKHOUSE_PASSWORD,
                    database=settings.QS_CLICKHOUSE_DB,
                    settings={'use_numpy': True}
                )
                logger.info("✅ ClickHouseLoader initialized (Sync driver wrapped in async)")

    def _get_snapshots_sync(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """内部同步查询快照"""
        # 匹配变体
        code_pure = stock_code.split('.')[0]
        code_variants = {
            stock_code, stock_code.lower(), code_pure,
            f"{code_pure}.SH", f"{code_pure}.sh",
            f"{code_pure}.SZ", f"{code_pure}.sz"
        }

        query = f"""
            SELECT
                snapshot_time, current_price, open_price, high_price, low_price,
                total_volume, total_amount,
                bid_price1, bid_volume1, bid_price2, bid_volume2,
                bid_price3, bid_volume3, bid_price4, bid_volume4,
                bid_price5, bid_volume5,
                ask_price1, ask_volume1, ask_price2, ask_volume2,
                ask_price3, ask_volume3, ask_price4, ask_volume4,
                ask_price5, ask_volume5
            FROM {self.snapshot_table}
            WHERE stock_code IN %(codes)s
              AND toDate(trade_date) = %(date)s
            ORDER BY snapshot_time ASC
        """
        data, columns = self.client.execute(
            query,
            {'codes': list(code_variants), 'date': trade_date},
            with_column_types=True
        )
        if not data:
            return pd.DataFrame()
        col_names = [c[0] for c in columns]
        return pd.DataFrame(data, columns=col_names)

    async def get_snapshots(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """异步包装: 获取快照"""
        if self.client is None:
            await self.initialize()

        # 强制代码标准化 (Gate-3 对齐)
        stock_code = DataValidator.clean_stock_code(stock_code)

        async with self._lock:
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    self._executor,
                    self._get_snapshots_sync,
                    stock_code,
                    trade_date
                )
            except Exception as e:
                logger.error(f"Failed to load snapshots for {stock_code}: {e}")
                return pd.DataFrame()

    def _get_ticks_sync(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """内部同步查询分笔"""
        # 修正: 业务逻辑中 tick_data_intraday 实际上保存了最近几天的数据
        # 而 tick_data (history) 可能是归档表或尚未迁移
        tables = [self.tick_table_intraday, self.tick_table_history]

        for target_table in tables:
            # 准备匹配变体: 原样, 纯数字, 纯数字+小写后缀, 纯数字+大写后缀
            code_pure = stock_code.split('.')[0]
            code_variants = {
                stock_code,                    # 300308.SZ
                stock_code.lower(),            # 300308.sz
                code_pure,                     # 300308
                f"{code_pure}.SH", f"{code_pure}.sh",
                f"{code_pure}.SZ", f"{code_pure}.sz"
            }

            query = f"""
                SELECT tick_time, price, volume, amount, direction, num
                FROM {target_table}
                WHERE stock_code IN %(codes)s
                  AND toDate(trade_date) = %(date)s
                ORDER BY tick_time ASC
            """
            logger.debug(f"Executing query on {target_table} for {stock_code}, {trade_date}")
            data, columns = self.client.execute(
                query,
                {'codes': list(code_variants), 'date': trade_date},
                with_column_types=True
            )
            if data:
                logger.info(f"DEBUG: Found {len(data)} rows in {target_table} for {stock_code}")
                col_names = [c[0] for c in columns]
                return pd.DataFrame(data, columns=col_names)

        return pd.DataFrame()

    async def get_ticks(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """异步包装: 获取分笔"""
        if self.client is None:
            await self.initialize()

        # 强制代码标准化 (Gate-3 对齐)
        stock_code = DataValidator.clean_stock_code(stock_code)

        async with self._lock:
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    self._executor,
                    self._get_ticks_sync,
                    stock_code,
                    trade_date
                )
            except Exception as e:
                logger.error(f"Failed to load ticks for {stock_code}: {e}")
                return pd.DataFrame()

    async def get_analysis_results(self, trade_date: str) -> pd.DataFrame:
        """获取指定日期的分析结果 (聚类与龙头)"""
        if self.client is None:
            await self.initialize()

        table = settings.QS_CLICKHOUSE_ANALYTICS_TABLE
        query = f"""
            SELECT trade_date, cluster_id, members, leaders, avg_divergence, member_count, trend_phase
            FROM {table}
            WHERE toDate(trade_date) = %(date)s
            ORDER BY cluster_id ASC
        """
        async with self._lock:
            try:
                loop = asyncio.get_event_loop()
                data, columns = await loop.run_in_executor(
                    self._executor,
                    lambda: self.client.execute(query, {'date': trade_date}, with_column_types=True)
                )
                if not data:
                    return pd.DataFrame()
                col_names = [c[0] for c in columns]
                return pd.DataFrame(data, columns=col_names)
            except Exception as e:
                logger.error(f"Failed to load analysis results for {trade_date}: {e}")
                return pd.DataFrame()

    async def close(self):
        """异步关闭连接"""
        async with self._lock:
            if self.client:
                self.client.disconnect()
                self.client = None
            self._executor.shutdown(wait=True)
            logger.info("✅ ClickHouseLoader connection closed")



"""
ClickHouse 数据加载适配器
负责高效加载分笔数据(Ticks)和快照数据(Snapshots)
"""
import logging
import pandas as pd
from typing import Optional, List
from datetime import datetime, date
from clickhouse_driver import Client
from config.settings import settings

logger = logging.getLogger(__name__)

class ClickHouseLoader:
    def __init__(self):
        self.client = Client(
            host=settings.QS_CLICKHOUSE_HOST,
            port=settings.QS_CLICKHOUSE_PORT,
            user=settings.QS_CLICKHOUSE_USER,
            password=settings.QS_CLICKHOUSE_PASSWORD,
            database=settings.QS_CLICKHOUSE_DB,
            settings={'use_numpy': True}  # 使用Numpy加速
        )
        self.snapshot_table = "snapshot_data_distributed"
        self.tick_table_history = "tick_data"
        self.tick_table_intraday = "tick_data_intraday"

    def get_snapshots(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """
        获取指定股票单日的快照数据
        Returns:
            DataFrame with columns: [time, price, open, high, low, vol, amount, bid1..5, ask1..5, etc]
        """
        query = f"""
            SELECT
                snapshot_time,
                current_price,
                open_price,
                high_price,
                low_price,
                total_volume,
                total_amount,
                bid_price1, bid_volume1,
                bid_price2, bid_volume2,
                bid_price3, bid_volume3,
                bid_price4, bid_volume4,
                bid_price5, bid_volume5,
                ask_price1, ask_volume1,
                ask_price2, ask_volume2,
                ask_price3, ask_volume3,
                ask_price4, ask_volume4,
                ask_price5, ask_volume5
            FROM {self.snapshot_table}
            WHERE stock_code = %(code)s
              AND toDate(trade_date) = %(date)s
            ORDER BY snapshot_time ASC
        """
        try:
            # Using execute with parameters dict for safety
            data, columns = self.client.execute(
                query, 
                {'code': stock_code, 'date': trade_date}, 
                with_column_types=True
            )
            if not data:
                return pd.DataFrame()
                
            col_names = [c[0] for c in columns]
            df = pd.DataFrame(data, columns=col_names)
            return df
            
        except Exception as e:
            logger.error(f"Failed to load snapshots for {stock_code} on {trade_date}: {e}")
            return pd.DataFrame()

    def get_ticks(self, stock_code: str, trade_date: str) -> pd.DataFrame:
        """
        获取指定股票单日的分笔成交数据
        自动判断读取历史表还是实时表
        """
        # 简单判断：如果是今天，查intraday；否则查history
        # 实际生产中可能需要更复杂的逻辑，这里简化处理
        target_table = self.tick_table_history
        if trade_date == datetime.now().strftime("%Y-%m-%d"):
             target_table = self.tick_table_intraday
             
        query = f"""
            SELECT
                tick_time,
                price,
                volume,
                amount,
                direction,
                num
            FROM {target_table}
            WHERE stock_code = %(code)s
              AND toDate(trade_date) = %(date)s
            ORDER BY tick_time ASC
        """
        try:
            data, columns = self.client.execute(
                query, 
                {'code': stock_code, 'date': trade_date}, 
                with_column_types=True
            )
            if not data:
                return pd.DataFrame()
            
            col_names = [c[0] for c in columns]
            df = pd.DataFrame(data, columns=col_names)
            return df
            
        except Exception as e:
            logger.error(f"Failed to load ticks for {stock_code} on {trade_date}: {e}")
            return pd.DataFrame()
            
    def close(self):
        self.client.disconnect()

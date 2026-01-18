
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import asynch
from asynch.pool import Pool as AsynchPool
import pytz

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class TickWriter:
    """
    分笔数据写入器
    职责:
    1. 数据格式转换 (map_direction, time formatting)
    2. 写入 ClickHouse (Intraday/History 表)
    """

    def __init__(self, clickhouse_pool: Optional[AsynchPool]):
        self.ch_pool = clickhouse_pool

    async def write(self, stock_code: str, trade_date: str, data: List[Dict[str, Any]]) -> int:
        """将数据写入 ClickHouse 并返回写入条数"""
        if not self.ch_pool or not data:
            return 0

        # 0. 确定目标表
        today_str = datetime.now(CST).strftime("%Y%m%d")
        target_table = "tick_data_intraday_local" if trade_date == today_str else "tick_data_local"
        
        try:
            # 1. 转换格式
            trade_date_obj = datetime.strptime(trade_date, "%Y%m%d").date()
            rows = []
            
            for item in data:
                time_str = str(item.get('time', '09:30'))
                if len(time_str) == 5: time_str += ":00"
                
                price = float(item.get('price', 0))
                # 处理 volume/vol 字段差异
                vol = int(item.get('volume', item.get('vol', 0)))
                
                rows.append((
                    stock_code,
                    trade_date_obj,
                    time_str,
                    price,
                    vol,
                    price * vol,  # amount approximation
                    self._map_direction(int(item.get('buyorsell', 2))),
                ))
            
            if not rows:
                return 0
            
            # 2. 写入 ClickHouse (分布式表)
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"INSERT INTO stock_data.{target_table} (stock_code, trade_date, tick_time, price, volume, amount, direction) VALUES",
                        rows
                    )
            
            # log summary only (detailed log in service)
            return len(rows)

        except Exception as e:
            logger.error(f"❌ {stock_code} 写入 {target_table} 失败: {e}")
            raise  # 抛出异常供上层处理状态

    def _map_direction(self, buyorsell: int) -> int:
        """映射买卖方向: 0=买 1=卖 2=中性"""
        if buyorsell == 0:
            return 0  # 买盘
        elif buyorsell == 1:
            return 1  # 卖盘
        else:
            return 2  # 中性

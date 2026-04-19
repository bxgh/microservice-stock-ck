"""
股票基础信息DAO
"""
import logging
import pandas as pd
from typing import List, Optional, Dict, Any
import aiomysql

logger = logging.getLogger(__name__)


class StockBasicDAO:
    """股票基础信息访问对象"""

    @staticmethod
    def get_ts_code(symbol: str) -> str:
        """从6位代码转换为TS代码格式"""
        symbol = str(symbol).zfill(6)
        if symbol.startswith(('6', '9')):
            return f"{symbol}.SH"
        elif symbol.startswith(('0', '3')):
            return f"{symbol}.SZ"
        elif symbol.startswith(('8', '4')):
            return f"{symbol}.BJ"
        return symbol

    async def get_all_stocks(self, pool: aiomysql.Pool) -> pd.DataFrame:
        """获取所有 A 股列表"""
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = "SELECT ts_code, symbol, name, area, industry, list_date FROM stock_basic_info WHERE list_status = 'L'"
                    await cursor.execute(query)
                    rows = await cursor.fetchall()
                    if not rows:
                        return pd.DataFrame()
                    return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    async def get_stock_info(self, pool: aiomysql.Pool, code: str) -> Optional[Dict[str, Any]]:
        """获取个股基本信息"""
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = "SELECT * FROM stock_basic_info WHERE ts_code = %s OR symbol = %s LIMIT 1"
                    await cursor.execute(query, (ts_code, code.zfill(6)))
                    row = await cursor.fetchone()
                    return row
        except Exception as e:
            logger.error(f"获取股票 {code} 信息失败: {e}")
            return None

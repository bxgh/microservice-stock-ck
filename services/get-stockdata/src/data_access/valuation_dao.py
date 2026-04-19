"""
个股估值指标DAO (PE/PB/市值等)
"""
import logging
import pandas as pd
from typing import Optional, List, Dict, Any
import aiomysql

logger = logging.getLogger(__name__)


class ValuationDAO:
    """个股估值数据访问对象"""

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

    async def get_latest_valuation(self, pool: aiomysql.Pool, code: str) -> Optional[Dict[str, Any]]:
        """获取个股最新估值指标"""
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 获取最新交易日的一条记录
                    query = """
                        SELECT * FROM daily_basic 
                        WHERE ts_code = %s 
                        ORDER BY trade_date DESC 
                        LIMIT 1
                    """
                    await cursor.execute(query, (ts_code,))
                    row = await cursor.fetchone()
                    return row
        except Exception as e:
            logger.error(f"获取股票 {code} 最新估值失败: {e}")
            return None

    async def get_valuation_history(
        self, 
        pool: aiomysql.Pool, 
        code: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """获取个股历史估值指标序列"""
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT * FROM daily_basic 
                        WHERE ts_code = %s 
                        AND trade_date BETWEEN %s AND %s
                        ORDER BY trade_date ASC
                    """
                    await cursor.execute(query, (ts_code, start_date, end_date))
                    rows = await cursor.fetchall()
                    if not rows:
                        return pd.DataFrame()
                    return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"获取股票 {code} 历史估值失败: {e}")
            return pd.DataFrame()

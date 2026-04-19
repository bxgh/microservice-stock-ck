"""
博弈与资金数据DAO (龙虎榜/北向资金等)
"""
import logging
import pandas as pd
from typing import Optional, List, Dict, Any
import aiomysql

logger = logging.getLogger(__name__)


class MarketDataDAO:
    """市场博弈及资金流向数据访问对象"""

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

    async def get_lhb_data(
        self, 
        pool: aiomysql.Pool, 
        code: str, 
        start_date: str = None, 
        end_date: str = None
    ) -> pd.DataFrame:
        """获取个股龙虎榜历史记录"""
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = "SELECT * FROM stock_lhb_daily WHERE ts_code = %s"
                    params = [ts_code]
                    if start_date:
                        query += " AND trade_date >= %s"
                        params.append(start_date)
                    if end_date:
                        query += " AND trade_date <= %s"
                        params.append(end_date)
                    query += " ORDER BY trade_date DESC"
                    
                    await cursor.execute(query, tuple(params))
                    rows = await cursor.fetchall()
                    if not rows:
                        return pd.DataFrame()
                    return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"获取股票 {code} 龙虎榜数据失败: {e}")
            return pd.DataFrame()

    async def get_north_funds_data(
        self, 
        pool: aiomysql.Pool, 
        code: str, 
        limit: int = 30
    ) -> pd.DataFrame:
        """获取个股北向资金持仓变动"""
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 假定表结构包含 ts_code, trade_date, vol, ratio 等
                    # 这里适配常用结构，具体字段在 STORY 4 比对时微调
                    query = """
                        SELECT * FROM stock_north_funds_daily 
                        WHERE ts_code = %s 
                        ORDER BY trade_date DESC 
                        LIMIT %s
                    """
                    await cursor.execute(query, (ts_code, limit))
                    rows = await cursor.fetchall()
                    if not rows:
                        return pd.DataFrame()
                    return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"获取股票 {code} 北向资金数据失败: {e}")
            return pd.DataFrame()

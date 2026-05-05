"""
板块与成份股数据DAO
"""
import logging
import pandas as pd
from typing import List, Optional, Dict, Any
import aiomysql

logger = logging.getLogger(__name__)


class SectorDAO:
    """板块/行业数据访问对象"""

    async def get_all_sectors(self, pool: aiomysql.Pool, sector_type: str = 'concept') -> pd.DataFrame:
        """获取所有板块列表"""
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 适配真实结构: sector_name, sector_type
                    query = "SELECT id, sector_name as name, sector_type as type FROM stock_sector_ths"
                    if sector_type:
                        query += " WHERE sector_type = %s"
                        await cursor.execute(query, (sector_type,))
                    else:
                        await cursor.execute(query)
                    
                    rows = await cursor.fetchall()
                    if not rows:
                        return pd.DataFrame()
                    return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"获取板块列表失败: {e}")
            return pd.DataFrame()

    async def get_sector_members(self, pool: aiomysql.Pool, sector_id: int) -> List[str]:
        """获取指定板块的所有成分股代码"""
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 表 stock_sector_cons_ths: sector_id, ts_code (stock)
                    query = "SELECT ts_code FROM stock_sector_cons_ths WHERE sector_id = %s"
                    await cursor.execute(query, (sector_id,))
                    rows = await cursor.fetchall()
                    if not rows:
                        return []
                    return [row['ts_code'] for row in rows]
        except Exception as e:
            logger.error(f"获取板块 ID {sector_id} 成分股失败: {e}")
            return []

    async def get_stock_sectors(self, pool: aiomysql.Pool, stock_code: str) -> pd.DataFrame:
        """获取个股所属的所有板块"""
        # 兼容性处理
        if '.' not in stock_code:
            if stock_code.startswith(('6', '9')):
                stock_code = f"{stock_code}.SH"
            else:
                stock_code = f"{stock_code}.SZ"
                
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT a.id, a.sector_name as name, a.sector_type as type 
                        FROM stock_sector_ths a
                        JOIN stock_sector_cons_ths b ON a.id = b.sector_id
                        WHERE b.ts_code = %s
                    """
                    await cursor.execute(query, (stock_code,))
                    rows = await cursor.fetchall()
                    if not rows:
                        return pd.DataFrame()
                    return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 所属板块失败: {e}")
            return pd.DataFrame()

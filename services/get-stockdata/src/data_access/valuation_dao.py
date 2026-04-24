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
        symbol = str(symbol).strip().upper()
        # 如果已经带有后缀，直接返回
        if symbol.endswith(('.SH', '.SZ', '.BJ')):
            return symbol
            
        code = symbol.zfill(6)
        if code.startswith(('6', '9')):
            return f"{code}.SH"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        elif code.startswith(('8', '4')):
            return f"{code}.BJ"
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
                    if row:
                        # 转换日期为字符串
                        if 'trade_date' in row and row['trade_date']:
                            row['trade_date'] = str(row['trade_date'])
                        # 添加 code 字段兼容老接口
                        row['code'] = ts_code.split('.')[0]
                    return row
        except Exception as e:
            logger.error(f"获取股票 {code} 最新估值失败: {e}")
            return None

    async def get_valuation_history(
        self, 
        pool: aiomysql.Pool, 
        code: str, 
        limit: int = 30,
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取个股历史估值指标序列"""
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    if start_date and end_date:
                        query = """
                            SELECT * FROM daily_basic 
                            WHERE ts_code = %s 
                            AND trade_date BETWEEN %s AND %s
                            ORDER BY trade_date DESC
                            LIMIT %s
                        """
                        await cursor.execute(query, (ts_code, start_date, end_date, limit))
                    else:
                        query = """
                            SELECT * FROM daily_basic 
                            WHERE ts_code = %s 
                            ORDER BY trade_date DESC 
                            LIMIT %s
                        """
                        await cursor.execute(query, (ts_code, limit))
                        
                    rows = await cursor.fetchall()
                    if not rows:
                        return []
                    
                    # 格式化结果
                    results = []
                    for row in rows:
                        item = dict(row)
                        if 'trade_date' in item and item['trade_date']:
                            item['trade_date'] = str(item['trade_date'])
                        item['code'] = ts_code.split('.')[0]
                        results.append(item)
                    
                    # 返回按日期升序排列的结果（通常前端需要时间轴升序）
                    return sorted(results, key=lambda x: x['trade_date'])
        except Exception as e:
            logger.error(f"获取股票 {code} 历史估值失败: {e}")
            return []

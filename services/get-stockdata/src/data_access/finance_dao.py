"""
三大会计报表财务数据DAO (聚合视图实现)
"""
import logging
import pandas as pd
from typing import Optional, Dict, Any, List
import aiomysql

logger = logging.getLogger(__name__)


class FinanceDAO:
    """个股财务数据访问对象 (资产负债/利润/现金流三表合一)"""

    # 业务字段映射表: DB字段 -> 业务展示字段 (完全适配当前 MySQL 真实 Schema)
    FIELD_MAP = {
        # 基础
        "ts_code": "code",
        "report_date": "report_date",
        "notice_date": "announce_date",
        
        # 利润表 (stock_income_statement)
        "total_revenue": "total_revenue",
        "operating_profit": "operating_profit",
        "net_profit": "net_profit",
        "parent_net_profit": "net_profit_parent",
        
        # 资产负债表 (stock_balance_sheet)
        "total_assets": "total_assets",
        "total_liabilities": "total_liabilities",
        "total_equity": "total_equity",
        
        # 现金流量表 (stock_cash_flow_statement)
        "net_operating_cash_flow": "net_cash_flow_operating",
        "net_investing_cash_flow": "net_cash_flow_investing",
        "net_financing_cash_flow": "net_cash_flow_financing",
        "free_cash_flow": "free_cash_flow",
        "cash_and_equivalents_at_end": "cash_at_end"
    }

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

    def _map_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """将库表原始记录映射为业务字段名"""
        if not row:
            return {}
        mapped = {}
        for db_key, biz_key in self.FIELD_MAP.items():
            if db_key in row:
                mapped[biz_key] = row[db_key]
        
        # 保留未映射但可能重要的元数据
        for k, v in row.items():
            if k not in self.FIELD_MAP and k not in mapped:
                mapped[k] = v
        return mapped

    async def get_derived_indicators(self, pool: aiomysql.Pool, code: str) -> Optional[Dict[str, Any]]:
        """
        获取计算好的财务衍生指标 (ROE, ROA, EPS 等)
        源表: stock_finance_indicators
        """
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT * FROM stock_finance_indicators 
                        WHERE ts_code = %s 
                        ORDER BY report_date DESC 
                        LIMIT 1
                    """
                    await cursor.execute(query, (ts_code,))
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取股票 {code} 衍生财务指标失败: {e}")
            return None

    async def get_latest_indicators(self, pool: aiomysql.Pool, code: str) -> Optional[Dict[str, Any]]:
        """
        聚合查询：获取个股最新三表合一财务指标
        """
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 先找出最新的一期报告日期
                    date_query = "SELECT MAX(report_date) as latest_date FROM stock_income_statement WHERE ts_code = %s"
                    await cursor.execute(date_query, (ts_code,))
                    result = await cursor.fetchone()
                    if not result or not result['latest_date']:
                        return None
                    
                    latest_date = result['latest_date']
                    
                    # 三表聚合查询
                    query = """
                        SELECT 
                            inc.*, 
                            bal.total_assets, bal.total_liabilities, bal.total_equity,
                            cf.net_operating_cash_flow, cf.net_investing_cash_flow, cf.net_financing_cash_flow, cf.free_cash_flow, cf.cash_and_equivalents_at_end
                        FROM stock_income_statement inc
                        LEFT JOIN stock_balance_sheet bal ON inc.ts_code = bal.ts_code AND inc.report_date = bal.report_date
                        LEFT JOIN stock_cash_flow_statement cf ON inc.ts_code = cf.ts_code AND inc.report_date = cf.report_date
                        WHERE inc.ts_code = %s AND inc.report_date = %s
                        LIMIT 1
                    """
                    await cursor.execute(query, (ts_code, latest_date))
                    row = await cursor.fetchone()
                    return self._map_fields(row)
        except Exception as e:
            logger.error(f"聚合获取股票 {code} 财务指标失败: {e}")
            return None

    async def get_financial_history(self, pool: aiomysql.Pool, code: str, limit: int = 8) -> List[Dict[str, Any]]:
        """获取个股历史财务报表聚合序列"""
        ts_code = self.get_ts_code(code)
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT 
                            inc.*, 
                            bal.total_assets, bal.total_liabilities, bal.total_equity,
                            cf.net_operating_cash_flow, cf.net_investing_cash_flow, cf.net_financing_cash_flow, cf.free_cash_flow, cf.cash_and_equivalents_at_end
                        FROM stock_income_statement inc
                        LEFT JOIN stock_balance_sheet bal ON inc.ts_code = bal.ts_code AND inc.report_date = bal.report_date
                        LEFT JOIN stock_cash_flow_statement cf ON inc.ts_code = cf.ts_code AND inc.report_date = cf.report_date
                        WHERE inc.ts_code = %s 
                        ORDER BY inc.report_date DESC 
                        LIMIT %s
                    """
                    await cursor.execute(query, (ts_code, limit))
                    rows = await cursor.fetchall()
                    return [self._map_fields(row) for row in rows]
        except Exception as e:
            logger.error(f"获取股票 {code} 历史财务失败: {e}")
            return []

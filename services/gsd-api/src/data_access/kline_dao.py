"""
K线数据MySQL访问对象
"""
import logging
import pandas as pd
from typing import Optional
import aiomysql
from datetime import datetime

logger = logging.getLogger(__name__)


class KLineDAO:
    """K线数据访问对象"""
    
    @staticmethod
    def get_ts_code(symbol: str) -> str:
        """从6位代码转换为TS代码格式"""
        symbol = str(symbol).strip().upper()
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

    async def get_kline_data(
        self,
        pool: aiomysql.Pool,
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjust: str = "0"
    ) -> pd.DataFrame:
        """
        从MySQL获取K线数据
        
        Args:
            pool: MySQL连接池
            stock_code: 股票代码（6位数字或带后缀）
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            frequency: 频率 (d=日线)
            adjust: 复权方式 (0=不复权, 1=前复权, 2=后复权)
            
        Returns:
            DataFrame with K-line data
        """
        if frequency != "d":
            logger.warning(f"目前只支持日线数据，频率参数 {frequency} 将被忽略")
        
        ts_code = self.get_ts_code(stock_code)
        
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 1. 获取基础K线数据
                    query = """
                        SELECT 
                            code,
                            trade_date as date,
                            open,
                            high,
                            low,
                            close,
                            volume,
                            amount,
                            turnover,
                            pct_chg
                        FROM stock_kline_daily
                        WHERE code = %s
                          AND trade_date BETWEEN %s AND %s
                        ORDER BY trade_date ASC
                    """
                    
                    await cursor.execute(query, (ts_code, start_date, end_date))
                    rows = await cursor.fetchall()
                    
                    if not rows:
                        logger.info(f"未找到股票 {ts_code} 在 {start_date} 至 {end_date} 的K线数据")
                        return pd.DataFrame()
                    
                    df = pd.DataFrame(rows)
                    
                    # 2. 如果需要复权，获取因子并合并
                    if adjust != "0":
                        factor_query = """
                            SELECT adjust_date, fore_adjust_factor, back_adjust_factor
                            FROM stock_adjust_factor
                            WHERE code = %s
                            ORDER BY adjust_date ASC
                        """
                        await cursor.execute(factor_query, (ts_code,))
                        factor_rows = await cursor.fetchall()
                        
                        if factor_rows:
                            df_factors = pd.DataFrame(factor_rows)
                            # 转换为 datetime 以便 merge_asof
                            df['date'] = pd.to_datetime(df['date'])
                            df_factors['adjust_date'] = pd.to_datetime(df_factors['adjust_date'])
                            
                            # 合并因子
                            df = pd.merge_asof(
                                df.sort_values('date'),
                                df_factors.sort_values('adjust_date'),
                                left_on='date',
                                right_on='adjust_date',
                                direction='backward'
                            )
                            
                            # 执行复权计算
                            factor_col = 'fore_adjust_factor' if adjust == "1" else 'back_adjust_factor'
                            for col in ['open', 'high', 'low', 'close']:
                                df[col] = df[col] * df[factor_col]
                                
                            # 还原日期，以便统一 API 响应格式
                            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                            
                        else:
                            logger.warning(f"股票 {ts_code} 未找到复权因子，返回原始数据")

                    logger.info(f"成功获取股票 {ts_code} 的 {len(df)} 条K线数据 (复权:{adjust})")
                    return df
                    
        except Exception as e:
            logger.error(f"查询K线数据失败: {e}")
            raise
    
    async def get_latest_kline(
        self,
        pool: aiomysql.Pool,
        stock_code: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        获取最新的N条K线数据
        
        Args:
            pool: MySQL连接池
            stock_code: 股票代码
            limit: 返回的K线条数
            
        Returns:
            DataFrame with latest K-line data
        """
        ts_code = self.get_ts_code(stock_code)
        
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT 
                            code,
                            trade_date as date,
                            open,
                            high,
                            low,
                            close,
                            volume,
                            amount,
                            turnover,
                            pct_chg
                        FROM stock_kline_daily
                        WHERE code = %s
                        ORDER BY trade_date DESC
                        LIMIT %s
                    """
                    
                    await cursor.execute(query, (ts_code, limit))
                    rows = await cursor.fetchall()
                    
                    if not rows:
                        logger.info(f"未找到股票 {ts_code} 的K线数据")
                        return pd.DataFrame()
                    
                    df = pd.DataFrame(rows)
                    # 反转顺序，使其按日期升序
                    df = df.iloc[::-1].reset_index(drop=True)
                    logger.info(f"成功获取股票 {ts_code} 的最新 {len(df)} 条K线数据")
                    return df
                    
        except Exception as e:
            logger.error(f"查询最新K线数据失败: {e}")
            raise

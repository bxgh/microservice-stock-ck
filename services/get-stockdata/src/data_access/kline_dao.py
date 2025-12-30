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
    
    async def get_kline_data(
        self,
        pool: aiomysql.Pool,
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d"
    ) -> pd.DataFrame:
        """
        从MySQL获取K线数据
        
        Args:
            pool: MySQL连接池
            stock_code: 股票代码（6位数字）
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            frequency: 频率 (d=日线, w=周线, m=月线) - 目前只支持日线
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount, etc.
        """
        if frequency != "d":
            logger.warning(f"目前只支持日线数据，频率参数 {frequency} 将被忽略")
        
        # 确保股票代码为6位
        stock_code = stock_code.zfill(6)
        
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
                          AND trade_date BETWEEN %s AND %s
                        ORDER BY trade_date ASC
                    """
                    
                    await cursor.execute(query, (stock_code, start_date, end_date))
                    rows = await cursor.fetchall()
                    
                    if not rows:
                        logger.info(f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的K线数据")
                        return pd.DataFrame()
                    
                    df = pd.DataFrame(rows)
                    logger.info(f"成功获取股票 {stock_code} 的 {len(df)} 条K线数据")
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
        stock_code = stock_code.zfill(6)
        
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
                    
                    await cursor.execute(query, (stock_code, limit))
                    rows = await cursor.fetchall()
                    
                    if not rows:
                        logger.info(f"未找到股票 {stock_code} 的K线数据")
                        return pd.DataFrame()
                    
                    df = pd.DataFrame(rows)
                    # 反转顺序，使其按日期升序
                    df = df.iloc[::-1].reset_index(drop=True)
                    logger.info(f"成功获取股票 {stock_code} 的最新 {len(df)} 条K线数据")
                    return df
                    
        except Exception as e:
            logger.error(f"查询最新K线数据失败: {e}")
            raise

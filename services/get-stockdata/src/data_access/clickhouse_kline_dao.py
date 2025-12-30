"""
ClickHouse K线数据访问对象
"""
import logging
import pandas as pd
from typing import Optional
import asynch.cursors

logger = logging.getLogger(__name__)


class ClickHouseKLineDAO:
    """ClickHouse K线数据访问对象"""
    
    async def get_kline_data(
        self,
        pool,
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjust: str = "0"
    ) -> pd.DataFrame:
        """
        从ClickHouse获取K线数据
        
        Args:
            pool: ClickHouse连接池
            stock_code: 股票代码（6位数字）
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            frequency: 频率 (d=日线)
            adjust: 复权方式 (0=不复权, 1=前复权, 2=后复权)
            
        Returns:
            DataFrame with K-line data
        """
        if frequency != "d":
            logger.warning(f"目前只支持日线数据，频率参数 {frequency} 将被忽略")
        
        stock_code = stock_code.zfill(6)
        
        # 处理股票代码模糊匹配（自动补全后缀）
        code_condition = """(
            stock_code = %(stock_code)s 
            OR stock_code = concat('sh.', %(stock_code)s)
            OR stock_code = concat('sz.', %(stock_code)s)
            OR stock_code = concat('bj.', %(stock_code)s)
        )"""
        
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(cursor=asynch.cursors.DictCursor) as cursor:
                    if adjust == "0":
                        # 不复权，直接查询
                        query = f"""
                            SELECT 
                                stock_code,
                                trade_date as date,
                                open_price as open,
                                high_price as high,
                                low_price as low,
                                close_price as close,
                                volume,
                                amount,
                                turnover_rate,
                                change_pct
                            FROM stock_kline_daily
                            WHERE {code_condition}
                              AND trade_date >= %(start_date)s
                              AND trade_date <= %(end_date)s
                            ORDER BY trade_date ASC
                        """
                    else:
                        # 复权查询，使用 ASOF JOIN 复权因子表
                        # adjust=1 (前复权), adjust=2 (后复权)
                        factor_col = "fore_factor" if adjust == "1" else "back_factor"
                        
                        query = f"""
                            SELECT 
                                k.stock_code,
                                k.trade_date as date,
                                k.open_price * ifNull(f.{factor_col}, 1.0) as open,
                                k.high_price * ifNull(f.{factor_col}, 1.0) as high,
                                k.low_price * ifNull(f.{factor_col}, 1.0) as low,
                                k.close_price * ifNull(f.{factor_col}, 1.0) as close,
                                k.volume,
                                k.amount,
                                k.turnover_rate,
                                k.change_pct
                            FROM stock_kline_daily k
                            ASOF LEFT JOIN (
                                SELECT stock_code, ex_date, fore_factor, back_factor 
                                FROM stock_adjust_factor
                            ) f
                            ON k.stock_code = f.stock_code AND k.trade_date >= f.ex_date
                            WHERE (
                                k.stock_code = %(stock_code)s 
                                OR k.stock_code = concat('sh.', %(stock_code)s)
                                OR k.stock_code = concat('sz.', %(stock_code)s)
                                OR k.stock_code = concat('bj.', %(stock_code)s)
                            )
                              AND k.trade_date >= %(start_date)s
                              AND k.trade_date <= %(end_date)s
                            ORDER BY k.trade_date ASC
                        """
                    
                    await cursor.execute(
                        query,
                        {
                            'stock_code': stock_code,
                            'start_date': start_date,
                            'end_date': end_date
                        }
                    )
                    
                    rows = await cursor.fetchall()
            
            if not rows:
                logger.info(f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的K线数据")
                return pd.DataFrame()
            
            df = pd.DataFrame(rows)
            logger.info(f"从ClickHouse获取股票 {stock_code} 的 {len(df)} 条K线数据 (复权:{adjust})")
            return df
            
        except Exception as e:
            logger.error(f"查询ClickHouse失败: {e}")
            raise
    
    async def get_latest_kline(
        self,
        pool,
        stock_code: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        获取最新的N条K线数据
        
        Args:
            pool: ClickHouse连接池
            stock_code: 股票代码
            limit: 返回的K线条数
            
        Returns:
            DataFrame with latest K-line data
        """
        stock_code = stock_code.zfill(6)
        
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(cursor_type=asynch.cursors.DictCursor) as cursor:
                    query = """
                        SELECT 
                            stock_code,
                            trade_date as date,
                            open_price as open,
                            high_price as high,
                            low_price as low,
                            close_price as close,
                            volume,
                            amount,
                            turnover_rate,
                            change_pct
                        FROM stock_kline_daily
                        WHERE (
                            stock_code = %(stock_code)s 
                            OR stock_code = concat('sh.', %(stock_code)s)
                            OR stock_code = concat('sz.', %(stock_code)s)
                            OR stock_code = concat('bj.', %(stock_code)s)
                        )
                        ORDER BY trade_date DESC
                        LIMIT %(limit)s
                    """
                    
                    await cursor.execute(
                        query,
                        {'stock_code': stock_code, 'limit': limit}
                    )
                    
                    rows = await cursor.fetchall()
            
            if not rows:
                logger.info(f"未找到股票 {stock_code} 的K线数据")
                return pd.DataFrame()
            
            df = pd.DataFrame(rows)
            
            # 反转顺序，按日期升序
            df = df.iloc[::-1].reset_index(drop=True)
            
            logger.info(f"从ClickHouse获取股票 {stock_code} 的最新 {len(df)} 条K线数据")
            return df
            
        except Exception as e:
            logger.error(f"查询ClickHouse最新K线失败: {e}")
            raise

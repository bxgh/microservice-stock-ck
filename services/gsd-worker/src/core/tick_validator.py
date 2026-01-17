
import logging
from datetime import datetime
from typing import Optional, List, Set
import asynch
from asynch.pool import Pool as AsynchPool
import pytz

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class TickDataValidator:
    """
    分笔数据质量校验器
    职责:
    1. 采前校验: 检查是否已达标 (check_quality, filter_need_repair)
    2. 采后校验: 金丝雀校验 (validate_canary)
    """
    
    # 核心权重股 (金丝雀)
    CANARY_STOCKS = {
        '000001', '600519', '600036', '601318', '000002', 
        '300059', '000725', '600000', '000858', '600276'
    }

    def __init__(self, clickhouse_pool: Optional[AsynchPool]):
        self.ch_pool = clickhouse_pool

    async def check_quality(self, stock_code: str, trade_date: str, min_tick_count: int = 2000) -> bool:
        """检查 ClickHouse 中数据是否存在且符合质量标准"""
        if not self.ch_pool:
            return False

        try:
            trade_date_str = datetime.strptime(
                trade_date.replace("-", ""), "%Y%m%d"
            ).strftime("%Y-%m-%d")
            
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT 
                            count() as tick_count,
                            min(tick_time) as min_time,
                            max(tick_time) as max_time
                        FROM tick_data_local 
                        WHERE stock_code = %(stock_code)s 
                          AND trade_date = %(trade_date)s
                    """, {"stock_code": stock_code, "trade_date": trade_date_str})
                    row = await cursor.fetchone()
                    
                    if not row or row[0] == 0:
                        return False
                    
                    tick_count, min_time, max_time = row
                    
                    # 质量标准
                    if tick_count < min_tick_count:
                        return False
                    
                    if min_time and max_time:
                        if min_time > "10:00:00" or max_time < "14:30:00":
                            return False
                    
                    logger.debug(f"✓ {stock_code} 数据已达标: {tick_count} ticks")
                    return True
        except Exception as e:
            logger.error(f"检查数据质量失败 {stock_code}: {e}")
            return False

    async def filter_need_repair(
        self, 
        stock_codes: List[str], 
        trade_date: str, 
        min_tick_count: int = 2000
    ) -> List[str]:
        """批量筛选出需要补采的股票"""
        if not stock_codes or not self.ch_pool:
            return stock_codes
        
        try:
            trade_date_str = datetime.strptime(
                trade_date.replace("-", ""), "%Y%m%d"
            ).strftime("%Y-%m-%d")
            
            # 构建 IN 条件
            codes_str = "','".join(stock_codes)
            
            # 使用参数化查询防止SQL注入
            placeholders = ','.join(['%(code{})s'.format(i) for i in range(len(stock_codes))])
            params = {f'code{i}': code for i, code in enumerate(stock_codes)}
            params['trade_date'] = trade_date_str
            
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT stock_code, count(), min(tick_time), max(tick_time)
                        FROM tick_data_local
                        WHERE stock_code IN ({placeholders})
                          AND trade_date = %(trade_date)s
                        GROUP BY stock_code
                    """, params)
                    rows = await cursor.fetchall()
                    
                    qualified_stocks = set()
                    for row in rows:
                        code, count, min_t, max_t = row
                        if count >= min_tick_count:
                            if min_t and max_t:
                                if min_t <= "10:00:00" and max_t >= "14:30:00":
                                    qualified_stocks.add(code)
                            else:
                                qualified_stocks.add(code)
                                
            need_repair = [c for c in stock_codes if c not in qualified_stocks]
            logger.info(f"📊 质量筛选: {len(stock_codes)} -> 需补采 {len(need_repair)}")
            return need_repair
            
        except Exception as e:
            logger.error(f"批量筛选失败: {e}，回退到全量列表")
            return stock_codes

    def validate_canary(self, stock_code: str, data: list, trade_date: Optional[str] = None) -> None:
        """金丝雀校验与历史非空校验"""
        if data:
            return

        # 1. 金丝雀校验
        if stock_code in self.CANARY_STOCKS:
             raise ValueError(f"CRITICAL: Suspicious empty data for canary stock {stock_code}")

        # 2. 历史非空校验
        if trade_date:
            try:
                query_date = datetime.strptime(str(trade_date), "%Y%m%d").date()
                today = datetime.now(CST).date()
                if query_date < today:
                    raise ValueError(f"Suspicious empty data for {stock_code} on historical date {trade_date}")
            except ValueError:
                pass

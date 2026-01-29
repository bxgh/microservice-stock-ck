import logging
from datetime import datetime
from typing import Optional, List, Set, Any
import pytz

# 尝试导入 asynch，如果不可用(如在纯逻辑环境中)则忽略，但在运行时需保证可用
try:
    from asynch.pool import Pool as AsynchPool
except ImportError:
    AsynchPool = Any

from gsd_shared.validation.standards import TickStandards

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')


class TickValidator:
    """
    分笔数据校验器 (从 gsd-worker 迁移并标准化)
    
    职责:
    1. 采前/采中校验: 检查数据是否已达标 (基于 TickStandards.Loose)
    2. 采后校验: 金丝雀校验
    """
    
    # 核心权重股 (金丝雀)
    CANARY_STOCKS = {
        '000001', '600519', '600036', '601318', '000002', 
        '300059', '000725', '600000', '000858', '600276'
    }

    def __init__(self, clickhouse_pool: Optional[AsynchPool]):
        self.ch_pool = clickhouse_pool

    async def check_quality(self, stock_code: str, trade_date: str) -> bool:
        """
        检查 ClickHouse 中数据是否存在且符合质量标准 (宽松标准)
        
        用于采集前的幂等性检查。
        """
        if not self.ch_pool:
            return False

        try:
            trade_date_str = datetime.strptime(
                trade_date.replace("-", ""), "%Y%m%d"
            ).strftime("%Y-%m-%d")
            
            # 根据日期选择查询表：当日 -> tick_data_intraday, 历史 -> tick_data
            today_str = datetime.now(CST).strftime("%Y-%m-%d")
            target_table = "tick_data_intraday" if trade_date_str == today_str else "tick_data"
            
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT 
                            count() as tick_count,
                            min(tick_time) as min_time,
                            max(tick_time) as max_time
                        FROM {target_table} 
                        WHERE stock_code = %(stock_code)s 
                          AND trade_date = %(trade_date)s
                    """, {"stock_code": stock_code, "trade_date": trade_date_str})
                    row = await cursor.fetchone()
                    
                    if not row or row[0] == 0:
                        return False
                    
                    tick_count, min_time, max_time = row
                    
                    # 使用标准化的宽松标准
                    if tick_count < TickStandards.Loose.MIN_COUNT:
                        return False
                    
                    if min_time and max_time:
                        # 只要在 10:00 - 14:30 之间有数据覆盖即可视为"存在"
                        # 避免因 9:25 缺失导致无限重采
                        if min_time > TickStandards.Loose.MIN_TIME or max_time < TickStandards.Loose.MAX_TIME:
                            return False
                    
                    logger.debug(f"✓ {stock_code} 数据已达标(宽松): {tick_count} ticks")
                    return True
        except Exception as e:
            logger.error(f"检查数据质量失败 {stock_code}: {e}")
            return False

    async def filter_need_repair(
        self, 
        stock_codes: List[str], 
        trade_date: str
    ) -> List[str]:
        """批量筛选出需要补采的股票 (基于宽松标准)"""
        if not stock_codes or not self.ch_pool:
            return stock_codes
        
        try:
            trade_date_str = datetime.strptime(
                trade_date.replace("-", ""), "%Y%m%d"
            ).strftime("%Y-%m-%d")
            
            # 使用参数化查询防止SQL注入
            placeholders = ','.join(['%(code{})s'.format(i) for i in range(len(stock_codes))])
            params = {f'code{i}': code for i, code in enumerate(stock_codes)}
            params['trade_date'] = trade_date_str
            
            # 根据日期选择查询表
            today_str = datetime.now(CST).strftime("%Y-%m-%d")
            target_table = "tick_data_intraday" if trade_date_str == today_str else "tick_data"
            
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT stock_code, count(), min(tick_time), max(tick_time)
                        FROM {target_table}
                        WHERE stock_code IN ({placeholders})
                          AND trade_date = %(trade_date)s
                        GROUP BY stock_code
                    """, params)
                    rows = await cursor.fetchall()
                    
                    qualified_stocks = set()
                    for row in rows:
                        code, count, min_t, max_t = row
                        
                        # 应用宽松标准
                        if count >= TickStandards.Loose.MIN_COUNT:
                            if min_t and max_t:
                                if min_t <= TickStandards.Loose.MIN_TIME and max_t >= TickStandards.Loose.MAX_TIME:
                                    qualified_stocks.add(code)
                            else:
                                qualified_stocks.add(code)
                                
            need_repair = [c for c in stock_codes if c not in qualified_stocks]
            logger.info(f"📊 质量筛选(Loose): {len(stock_codes)} -> 需补采 {len(need_repair)}")
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

    async def check_intraday_coverage(
        self, 
        stock_codes: List[str], 
        trade_date: str,
        session: str = 'close'
    ) -> tuple[int, int, List[str]]:
        """
        检查盘中分笔表的覆盖率
        
        Args:
            stock_codes: 预期的股票代码列表
            trade_date: 交易日期 (格式: YYYY-MM-DD 或 YYYYMMDD)
            session: 'noon' (检查 09:25-11:30) 或 'close' (检查 09:25-15:00)
        
        Returns:
            (expected_count, actual_count, missing_codes)
        """
        if not self.ch_pool or not stock_codes:
            return len(stock_codes), 0, stock_codes
        
        try:
            # 格式化日期
            if len(trade_date) == 8:
                trade_date_str = datetime.strptime(trade_date, "%Y%m%d").strftime("%Y-%m-%d")
            else:
                trade_date_str = trade_date
            
            # 构建时间过滤条件
            time_filter = "tick_time <= '11:30:00'" if session == 'noon' else "1=1"
            
            # 根据 session 设定最小记录数阈值
            # Noon (120mins): 设为 110 做宽松检查
            # Close (240mins): 设为 230 做完整性检查 (参照 IntradayPostMarket 标准)
            min_count = 110 if session == 'noon' else 230
            
            # 查询 tick_data_intraday 表
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT DISTINCT stock_code 
                        FROM tick_data_intraday 
                        WHERE trade_date = %(trade_date)s AND {time_filter}
                        GROUP BY stock_code
                        HAVING count() >= %(min_count)s AND min(tick_time) <= '09:30:00'
                    """, {"trade_date": trade_date_str, "min_count": min_count})
                    rows = await cursor.fetchall()
                    actual_codes = {row[0] for row in rows}
            
            # 计算缺失
            expected_set = set(stock_codes)
            missing_codes = list(expected_set - actual_codes)
            
            logger.info(f"📊 盘中分笔覆盖率检查 ({session}, min_ticks={min_count}): {len(actual_codes)}/{len(expected_set)} ({len(actual_codes)/len(expected_set)*100:.1f}%)")
            
            return len(expected_set), len(actual_codes), missing_codes
            
        except Exception as e:
            logger.error(f"❌ 检查盘中分笔覆盖率失败: {e}")
            return len(stock_codes), 0, stock_codes

    async def validate_stock(self, stock_code: str, trade_date: str, kline_ref: Optional[dict] = None) -> dict:
        """
        个股分笔数据全维度校验 (Level 1-3)
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期
            kline_ref: 参考日K数据, 如 {"close": 10.5, "volume": 1234500}
            
        Returns:
            dict: {
                "code": str,
                "status": "PASS" | "FAIL",
                "level": "L1" | "L2" | "L3" | None,
                "reasons": list,
                "action": "REPAIR" | "NONE"
            }
        """
        # 结果初始化
        result = {
            "code": stock_code,
            "status": "PASS",
            "level": None,
            "reasons": [],
            "action": "NONE"
        }

        if not self.ch_pool:
            result.update({"status": "FAIL", "reasons": ["No DB Connection"], "action": "REPAIR"})
            return result

        try:
            # 格式化日期 & 确定表名
            if len(trade_date) == 8:
                trade_date_str = datetime.strptime(trade_date, "%Y%m%d").strftime("%Y-%m-%d")
            else:
                trade_date_str = trade_date
            
            today_str = datetime.now(CST).strftime("%Y-%m-%d")
            target_table = "tick_data_intraday" if trade_date_str == today_str else "tick_data"
            
            # 1. 基础数据聚合 (覆盖 L1, L2, L3 需要的基础指标)
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT 
                            count() as tick_count,
                            min(tick_time) as first_tick,
                            max(tick_time) as last_tick,
                            countDistinct(substring(tick_time, 1, 5)) as active_minutes,
                            sum(volume) as total_volume,
                            argMax(price, tick_time) as last_price
                        FROM {target_table}
                        WHERE stock_code = %(code)s AND trade_date = %(date)s
                    """, {"code": stock_code, "date": trade_date_str})
                    row = await cursor.fetchone()
            
            # --- Level 1: Existence ---
            if not row or row[0] == 0:
                result.update({
                    "status": "FAIL",
                    "level": "L1",
                    "reasons": ["Missing: No Data found in ClickHouse"],
                    "action": "REPAIR"
                })
                return result

            tick_count, first_tick, last_tick, active_minutes, total_volume, last_price = row
            std = TickStandards.IntradayPostMarket

            # --- Level 2: Completeness ---
            l2_reasons = []
            
            # 活跃分钟数
            if active_minutes < std.MIN_ACTIVE_MINUTES:
                l2_reasons.append(f"Low Active Minutes ({active_minutes}/{std.MIN_ACTIVE_MINUTES})")
            
            # 开盘时间
            f_cmp = first_tick if len(first_tick) == 8 else f"{first_tick}:00"
            if f_cmp > std.MIN_TIME:
                l2_reasons.append(f"Late Open ({first_tick} > {std.MIN_TIME})")

            # 收盘时间
            l_cmp = last_tick if len(last_tick) == 8 else f"{last_tick}:00"
            if l_cmp < std.MAX_TIME:
                l2_reasons.append(f"Early Close ({last_tick} < {std.MAX_TIME})")
            
            if l2_reasons:
                result.update({
                    "status": "FAIL",
                    "level": "L2",
                    "reasons": l2_reasons,
                    "action": "REPAIR"
                })
                return result

            # --- Level 3: Accuracy ---
            if kline_ref:
                l3_reasons = []
                
                # 价格对账 (容忍 0.015 误差)
                ref_close = kline_ref.get("close")
                if ref_close is not None:
                    if abs(last_price - ref_close) > 0.015:
                        l3_reasons.append(f"Price Mismatch: Tick={last_price} vs KLine={ref_close}")
                
                # 成交量对账 (容忍 5% 误差)
                ref_vol = kline_ref.get("volume")
                if ref_vol is not None and ref_vol > 0:
                    vol_diff_rate = abs(total_volume - ref_vol) / ref_vol
                    if vol_diff_rate > 0.05:
                        l3_reasons.append(f"Volume Mismatch: Tick={total_volume} vs KLine={ref_vol} (Diff={vol_diff_rate:.1%})")

                if l3_reasons:
                    result.update({
                        "status": "FAIL",
                        "level": "L3",
                        "reasons": l3_reasons,
                        "action": "REPAIR"
                    })
                    return result

            # 全部通过
            return result

        except Exception as e:
            logger.error(f"Validation failed for {stock_code}: {e}", exc_info=True)
            result.update({
                "status": "FAIL",
                "reasons": [f"Runtime Error: {str(e)}"],
                "action": "REPAIR"
            })
            return result

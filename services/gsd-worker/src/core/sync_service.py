"""
K线数据同步核心服务
"""
import asyncio
import aiomysql
import asynch
import os
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from core.exceptions import DataMismatchException
from gsd_shared.validators import is_valid_a_stock

logger = logging.getLogger(__name__)

# 常量定义
CLICKHOUSE_DELETE_WAIT_SECONDS = 2  # ClickHouse 异步删除操作等待时间
MYSQL_QUERY_RETRY_MAX_ATTEMPTS = 3  # MySQL 查询重试最大次数
MYSQL_QUERY_RETRY_WAIT_SECONDS = 5  # MySQL 查询重试等待时间

class KLineSyncService:
    """K线数据同步服务"""
    
    def __init__(self):
        self.mysql_pool = None
        self.clickhouse_pool = None
        self.redis = None
    
    async def initialize(self):
        """初始化数据库连接池"""
        # Redis
        try:
            from data_access.redis_pool import RedisPoolManager
            self.redis = await RedisPoolManager.get_instance().get_redis()
        except ImportError:
            logger.warning("RedisPoolManager not found, skipping Redis init")
            self.redis = None

        # 环境变量适配：优先使用 GSD_DB_ 前缀，兼容 MYSQL_ 前缀
        db_host = os.getenv('MYSQL_HOST') or os.getenv('GSD_DB_HOST')
        db_port = int(os.getenv('MYSQL_PORT') or os.getenv('GSD_DB_PORT', 3306))
        db_user = os.getenv('MYSQL_USER') or os.getenv('GSD_DB_USER')
        db_password = os.getenv('MYSQL_PASSWORD') or os.getenv('GSD_DB_PASSWORD')
        db_name = os.getenv('MYSQL_DATABASE') or os.getenv('GSD_DB_NAME')

        # 开发环境强制使用本地隧道 (Sync with main.py logic)
        if os.getenv('ENVIRONMENT') == 'development':
            if db_host != '127.0.0.1':
                logger.info("! 开发环境检测：强制使用GOST隧道 (127.0.0.1:36301)")
                db_host = '127.0.0.1'
                db_port = 36301

        # MySQL连接池
        self.mysql_pool = await aiomysql.create_pool(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            db=db_name,
            charset='utf8mb4',
            minsize=1,
            maxsize=5
        )
        logger.info(f"✓ MySQL连接池已创建 ({db_host}:{db_port})")
        
        # ClickHouse连接池
        self.clickhouse_pool = await asynch.create_pool(
            host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
            port=int(os.getenv('CLICKHOUSE_PORT', 9000)),
            user=os.getenv('CLICKHOUSE_USER', 'admin'),
            password=os.getenv('CLICKHOUSE_PASSWORD', 'admin123'),
            database=os.getenv('CLICKHOUSE_DB', 'stock_data')
        )
        logger.info("✓ ClickHouse连接池已创建")
    
    async def close(self):
        """关闭连接池"""
        if self.mysql_pool:
            self.mysql_pool.close()
            await self.mysql_pool.wait_closed()
        if self.clickhouse_pool:
            self.clickhouse_pool.close()
            await self.clickhouse_pool.wait_closed()
        logger.info("连接池已关闭")

    async def _update_status(self, status: str, message: str = "", progress: float = 0.0, extra: dict = None):
        """更新同步状态到Redis"""
        try:
            if not self.redis:
                return
            
            payload = {
                "status": status,
                "message": message,
                "progress": f"{progress:.1f}",
                "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            if extra:
                payload.update(extra)
            
            # 使用 update_at 作为简单的防抖或直接写入
            await self.redis.hset("sync:status:kline", mapping=payload)
            
            # Set expiry for status key (e.g. 7 days) so it doesn't rot forever
            await self.redis.expire("sync:status:kline", 60 * 60 * 24 * 7)
            
        except Exception as e:
            logger.warning(f"Failed to update redis status: {e}")

    async def _log_to_db(self, status: str, records: int, message: str, duration: float, task_name: str = "kline_daily_sync"):
        """记录执行结果到 MySQL"""
        try:
            if not self.mysql_pool:
                logger.warning("MySQL pool not available for logging")
                return

            async with self.mysql_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO sync_execution_logs 
                        (task_name, status, records_processed, details, duration_seconds, execution_time)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """
                    await cursor.execute(sql, (
                        task_name, 
                        status.upper(), 
                        records, 
                        message, 
                        duration
                    ))
                    await conn.commit()
            logger.info("✓ 执行日志已写入 MySQL")
        except Exception as e:
            logger.error(f"写入执行日志失败: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiomysql.OperationalError, aiomysql.InterfaceError, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _fetch_from_mysql_with_retry(self, query: str, params: tuple = None):
        """
        带重试的 MySQL 查询
        
        P1 改进: 应对网络抖动，使用指数退避重试
        - 最多重试 3 次
        - 等待时间: 2s, 4s, 8s (指数增长)
        - 仅重试网络相关错误
        """
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()


    async def sync_full(self, batch_size: int = 10000):
        """
        全量同步：从MySQL同步所有K线数据到ClickHouse
        """
        logger.info("开始全量同步...")
        await self._update_status("running", "开始全量同步...", 0.0)
        
        try:
            total_synced = 0
            
            async with self.mysql_pool.acquire() as mysql_conn:
                async with mysql_conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT 
                            code, trade_date, open, high, low, close,
                            volume, amount, turnover, pct_chg
                        FROM stock_kline_daily
                        ORDER BY trade_date, code
                    """
                    
                    await cursor.execute(query)
                    
                    while True:
                        rows = await cursor.fetchmany(batch_size)
                        if not rows:
                            break
                            
                        await self._insert_to_clickhouse_enhanced(rows)
                        total_synced += len(rows)
                        
                        logger.info(f"已同步: {total_synced:,} 条")
                        await self._update_status("running", f"同步中: {total_synced:,}", 0.0)

            logger.info(f"✓ 全量同步完成，共 {total_synced:,} 条")
            await self._update_status("success", f"全量同步完成，共 {total_synced:,} 条", 100.0)

        except Exception as e:
            logger.error(f"全量同步失败: {e}")
            await self._update_status("failed", f"全量同步失败: {str(e)}", 0.0)
            raise e
    
    async def sync_smart_incremental(self, forced_date: str = None):
        """
        智能增量同步（自愈版）：
        1. 查询 ClickHouse 最大日期及其记录数
        2. 与 MySQL 云端数据对比，如果不一致则删除该日期数据
        3. 同步所有大于最大日期的数据
        """
        start_time = datetime.now()
        duration = 0.0
        logger.info(f"开始智能增量同步（模式={'强制同步' if forced_date else '自动增量'}, 日期={forced_date or 'latest'})...")
        await self._update_status("running", "正在检查数据完整性...", 0.0)
        
        try:
            re_sync_date = None
            clickhouse_max_date = None

            if forced_date:
                # 如果指定了强制日期，直接跳过自动检测，标记为需要重采样
                clickhouse_max_date = forced_date
                re_sync_date = forced_date
                logger.info(f"🔧 指定强制同步日期: {forced_date}，将执行删除后重采")
            else:
                # 第1步：查询 ClickHouse 中的最大交易日期
                async with self.clickhouse_pool.acquire() as ch_conn:
                    async with ch_conn.cursor() as cursor:
                        await cursor.execute("SELECT MAX(trade_date) as max_date FROM stock_kline_daily")
                        result = await cursor.fetchone()
                        clickhouse_max_date = result[0] if result and result[0] else None
                
                if not clickhouse_max_date:
                    logger.warning("ClickHouse 表为空，将执行全量同步")
                    await self.sync_full()
                    return
                
                logger.info(f"ClickHouse 自动检测最大日期: {clickhouse_max_date}")

            # 第2步：查询该日期在 ClickHouse 和 MySQL 中的记录数对比（如果是 forced_date 则必须对比以决定是否删除）
            async with self.clickhouse_pool.acquire() as clickhouse_conn:
                async with clickhouse_conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT count() FROM stock_kline_daily WHERE trade_date = %(date)s",
                        {'date': clickhouse_max_date}
                    )
                    clickhouse_record_count = (await cursor.fetchone())[0]
            
            async with self.mysql_pool.acquire() as mysql_conn:
                async with mysql_conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT COUNT(*) FROM stock_kline_daily WHERE trade_date = %s",
                        (clickhouse_max_date,)
                    )
                    mysql_record_count = (await cursor.fetchone())[0]
            
            logger.info(f"日期 {clickhouse_max_date} 记录数对比: ClickHouse={clickhouse_record_count}, MySQL={mysql_record_count}")
            
            # 第3步：如果不一致或强制指定了日期，删除 ClickHouse 中该日期的数据并重来
            if forced_date or (clickhouse_record_count != mysql_record_count):
                logger.warning(f"⚠️ {'强制同步' if forced_date else '数据不一致'}，执行删除重采: {clickhouse_max_date}")
                await self.delete_kline_by_date(clickhouse_max_date)
                re_sync_date = clickhouse_max_date
                
                # 记录需要额外补采的日期
                re_sync_date = clickhouse_max_date
                
                # 重新查询最大日期（删除后可能变化，但由于 ClickHouse 异步删除，此处查询仅作日志参考）
                async with self.clickhouse_pool.acquire() as clickhouse_conn:
                    async with clickhouse_conn.cursor() as cursor:
                        # 排除掉刚刚删除的日期，寻找真正的历史最大点
                        await cursor.execute(
                            "SELECT MAX(trade_date) FROM stock_kline_daily WHERE trade_date < %(date)s",
                            {"date": re_sync_date}
                        )
                        result = await cursor.fetchone()
                        clickhouse_max_date = result[0] if result and result[0] else None
                
                if clickhouse_max_date:
                    logger.info(f"删除后（不含目标日）新的历史最大日期: {clickhouse_max_date}")
                else:
                    logger.info("删除后表为空，将从头同步")
            
            # 第4步：同步数据
            # 如果有 re_sync_date，则必须包含该日（使用 >=）
            # 否则从 clickhouse_max_date 之后开始（使用 >）
            if re_sync_date:
                query = """
                    SELECT 
                        code, trade_date, open, high, low, close,
                        volume, amount, turnover, pct_chg
                    FROM stock_kline_daily
                    WHERE trade_date >= %s
                    ORDER BY trade_date, code
                """
                params = (re_sync_date,)
            elif clickhouse_max_date:
                query = """
                    SELECT 
                        code, trade_date, open, high, low, close,
                        volume, amount, turnover, pct_chg
                    FROM stock_kline_daily
                    WHERE trade_date > %s
                    ORDER BY trade_date, code
                """
                params = (clickhouse_max_date,)
            else:
                query = """
                    SELECT 
                        code, trade_date, open, high, low, close,
                        volume, amount, turnover, pct_chg
                    FROM stock_kline_daily
                    ORDER BY trade_date, code
                """
                params = ()

            rows = await self._fetch_from_mysql_with_retry(query, params)
            
            duration = (datetime.now() - start_time).total_seconds()
            if rows:
                await self._insert_to_clickhouse_enhanced(rows)
                
                min_date = min(row['trade_date'] for row in rows)
                max_date = max(row['trade_date'] for row in rows)
                msg = f"智能增量同步完成：{len(rows):,} 条记录 ({min_date} ~ {max_date})"
                logger.info(f"✓ {msg}")
                await self._update_status("success", msg, 100.0, {"new_records": len(rows), "date_range": f"{min_date}~{max_date}"})
                await self._log_to_db("SUCCESS", len(rows), msg, duration)
            else:
                msg = "无新数据需要同步，ClickHouse 已是最新状态"
                logger.info(f"✓ {msg}")
                await self._update_status("success", msg, 100.0, {"new_records": 0})
                await self._log_to_db("SUCCESS", 0, msg, duration)

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_status("failed", f"智能同步失败: {str(e)}", 0.0)
            await self._log_to_db("FAILED", 0, str(e), duration)
            raise e
    
    async def delete_kline_by_date(self, trade_date):
        """物理删除 ClickHouse 中指定日期的数据"""
        logger.info(f"正在删除 ClickHouse 中的数据: {trade_date}")
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "ALTER TABLE stock_kline_daily_local ON CLUSTER stock_cluster DELETE WHERE trade_date = %(date)s",
                    {'date': trade_date}
                )
                logger.info(f"✓ 已发送删除指令 (trade_date={trade_date})，等待异步处理...")
                await asyncio.sleep(CLICKHOUSE_DELETE_WAIT_SECONDS)

    async def sync_by_date(self, trade_date: str = None):
        """
        按日期修复（已废弃参数，现在统一使用智能同步）
        
        Args:
            trade_date: 保留参数用于兼容性，实际不使用
        """
        if trade_date:
            logger.info(f"收到日期参数 {trade_date}，但现在使用智能自愈同步，将自动检测并修复所有不一致数据")
        
        # 直接调用智能同步，它会自动检测并修复不一致的数据
        await self.sync_smart_incremental()

    async def sync_by_stock_codes(self, stock_codes: list[str]):
        """
        按股票代码同步：从MySQL同步指定股票的全部历史数据到ClickHouse
        
        用途: 个股数据重建后的同步
        """
        start_time = datetime.now()
        duration = 0.0
        logger.info(f"开始按股票代码同步: {stock_codes}")
        await self._update_status("running", f"正在同步 {len(stock_codes)} 只股票...", 0.0)
        
        try:
            # 构建 SQL 查询
            placeholders = ','.join(['%s'] * len(stock_codes))
            query = f"""
                SELECT 
                    code, trade_date, open, high, low, close,
                    volume, amount, turnover, pct_chg
                FROM stock_kline_daily
                WHERE code IN ({placeholders})
                ORDER BY code, trade_date
            """
            
            rows = await self._fetch_from_mysql_with_retry(query, tuple(stock_codes))
            
            duration = (datetime.now() - start_time).total_seconds()
            if rows:
                await self._insert_to_clickhouse_enhanced(rows)
                
                # 统计每只股票的记录数
                from collections import Counter
                stock_counts = Counter(row['code'] for row in rows)
                
                msg = f"按股票代码同步完成：{len(rows):,} 条记录，{len(stock_counts)} 只股票"
                logger.info(f"✓ {msg}")
                logger.info(f"详情: {dict(stock_counts)}")
                
                await self._update_status("success", msg, 100.0, {
                    "total_records": len(rows),
                    "stock_counts": dict(stock_counts)
                })
                await self._log_to_db("SUCCESS", len(rows), msg, duration)
            else:
                msg = f"指定股票无数据: {stock_codes}"
                logger.warning(msg)
                await self._update_status("success", msg, 100.0, {"total_records": 0})
                await self._log_to_db("SUCCESS", 0, msg, duration)
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_status("failed", f"按股票代码同步失败: {str(e)}", 0.0)
            await self._log_to_db("FAILED", 0, str(e), duration)
            raise e
    
    async def sync_by_created_at(self, lookback_hours: int = 48, batch_size: int = 10000, start_time: Optional[datetime] = None):
        """
        基于 created_at 时间戳的增量同步 (使用游标分页优化性能)
        """
        if start_time:
            log_msg = f"开始基于 created_at 的增量同步（从 {start_time} 开始）..."
        else:
            log_msg = f"开始基于 created_at 的增量同步（回溯{lookback_hours}小时）..."
            start_time = datetime.now() - timedelta(hours=lookback_hours)
            
        logger.info(log_msg)
        await self._update_status("running", log_msg, 0.0)
        
        try:
            async with self.mysql_pool.acquire() as mysql_conn:
                async with mysql_conn.cursor(aiomysql.DictCursor) as cursor:
                    # 1. 统计总数 (可选)
                    try:
                        count_query = "SELECT COUNT(*) as cnt FROM stock_kline_daily WHERE created_at >= %s"
                        await cursor.execute(count_query, (start_time,))
                        total = (await cursor.fetchone())['cnt']
                        logger.info(f"待同步总记录数: {total:,}")
                        if total == 0:
                            await self._update_status("success", "无新数据需要同步", 100.0)
                            return
                    except Exception as e:
                        logger.warning(f"统计总数失败: {e}")
                        total = 0

                    # 2. 游标分页同步
                    last_created_at = start_time
                    last_code = ''
                    last_trade_date = ''
                    synced = 0
                    is_first_batch = True
                    
                    while True:
                        if is_first_batch:
                            query = f"""
                                SELECT code, trade_date, open, high, low, close, volume, amount, turnover, pct_chg, created_at
                                FROM stock_kline_daily
                                WHERE created_at >= %s
                                ORDER BY created_at ASC, code ASC, trade_date ASC
                                LIMIT {batch_size}
                            """
                            params = (start_time,)
                        else:
                            query = f"""
                                SELECT code, trade_date, open, high, low, close, volume, amount, turnover, pct_chg, created_at
                                FROM stock_kline_daily
                                WHERE (created_at > %s) 
                                   OR (created_at = %s AND code > %s)
                                   OR (created_at = %s AND code = %s AND trade_date > %s)
                                ORDER BY created_at ASC, code ASC, trade_date ASC
                                LIMIT {batch_size}
                            """
                            params = (last_created_at, last_created_at, last_code, last_created_at, last_code, last_trade_date)
                        
                        await cursor.execute(query, params)
                        rows = await cursor.fetchall()
                        
                        if not rows:
                            break
                        
                        last_row = rows[-1]
                        last_created_at = last_row['created_at']
                        last_code = last_row['code']
                        last_trade_date = last_row['trade_date']
                        is_first_batch = False
                        
                        await self._insert_to_clickhouse(rows)
                        
                        synced += len(rows)
                        if total > 0:
                            progress = min(99.9, (synced / total) * 100)
                            logger.info(f"进度: {synced:,}/{total:,} ({progress:.1f}%)")
                            await self._update_status("running", f"同步中: {synced:,}/{total:,}", progress)
                        else:
                            logger.info(f"进度: 已同步 {synced:,} 条")
                
                logger.info(f"✓ 基于 created_at 同步完成，共 {synced:,} 条")
                await self._update_status("success", f"同步完成，共 {synced:,} 条", 100.0, {"total_synced": synced})

        except Exception as e:
            await self._update_status("failed", f"同步出错: {str(e)}", 0.0)
            raise e
    
    async def sync_adjust_factors(self, batch_size: int = 5000):
        """
        同步复权因子数据
        """
        start_time = datetime.now()
        logger.info("开始同步复权因子...")
        await self._update_status("running", "开始同步复权因子...", 0.0)
        
        try:
            # 1. 查询ClickHouse最大除权日期
            async with self.clickhouse_pool.acquire() as ch_conn:
                async with ch_conn.cursor() as cursor:
                    await cursor.execute("SELECT MAX(adjust_date) FROM stock_adjust_factor")
                    result = await cursor.fetchone()
                    ch_max_date = result[0] if result and result[0] else None # '1900-01-01' logic in date check

            # 构建查询条件
            if ch_max_date:
                logger.info(f"ClickHouse复权因子最大日期: {ch_max_date}")
                where_clause = f"WHERE adjust_date > '{ch_max_date}'"
            else:
                logger.info("ClickHouse无复权因子数据，执行全量同步")
                where_clause = ""
            
            # 2. 获取MySQL待同步总数
            async with self.mysql_pool.acquire() as mysql_conn:
                async with mysql_conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(f"SELECT COUNT(*) as cnt FROM stock_adjust_factor {where_clause}")
                    total = (await cursor.fetchone())['cnt']
                    logger.info(f"待同步复权因子总数: {total:,}")
                    
                    if total == 0:
                        await self._update_status("success", "无新复权因子数据", 100.0)
                        await self._log_to_db("SUCCESS", 0, "无新复权因子数据", (datetime.now() - start_time).total_seconds())
                        return

                    # 3. 分批同步
                    offset = 0
                    synced = 0
                    while offset < total:
                        query = f"""
                            SELECT code, adjust_date, fore_adjust_factor, back_adjust_factor
                            FROM stock_adjust_factor
                            {where_clause}
                            ORDER BY adjust_date, code
                            LIMIT {batch_size} OFFSET {offset}
                        """
                        await cursor.execute(query)
                        rows = await cursor.fetchall()
                        
                        if not rows:
                            break
                        
                        await self._insert_factors_to_clickhouse(rows)
                        
                        synced += len(rows)
                        offset += batch_size
                        progress = min(99.9, (synced / total) * 100)
                        logger.info(f"复权因子进度: {synced:,}/{total:,} ({progress:.1f}%)")
                        await self._update_status("running", f"同步中: {synced:,}/{total:,}", progress)

            duration = (datetime.now() - start_time).total_seconds()
            msg = f"复权因子同步完成，共 {synced:,} 条"
            logger.info(f"✓ {msg}")
            await self._update_status("success", msg, 100.0, {"total_synced": synced})
            await self._log_to_db("SUCCESS", synced, msg, duration)

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_status("failed", f"同步出错: {str(e)}", 0.0)
            await self._log_to_db("FAILED", 0, str(e), duration)
            raise e
    
    def _normalize_code_for_mysql(self, code: str) -> str:
        """
        归一化股票代码用于 MySQL 查询
        600000.SH -> sh.600000
        000001.SZ -> sz.000001
        """
        if not code:
            return code
        
        code = code.strip().upper()
        if '.' in code:
            parts = code.split('.')
            if len(parts) == 2:
                # 处理 600000.SH 这种格式
                if parts[1] in ['SH', 'SZ', 'BJ']:
                    symbol, market = parts
                    return f"{market.lower()}.{symbol}"
                # 处理 SH.600000 这种格式
                elif parts[0] in ['SH', 'SZ', 'BJ']:
                    market, symbol = parts
                    return f"{market.lower()}.{symbol}"
        
        return code.lower()

    async def _insert_factors_to_clickhouse(self, rows: list):
        """批量插入复权因子到 ClickHouse"""
        if not rows:
            return
        
        async with self.clickhouse_pool.acquire() as ch_conn:
            async with ch_conn.cursor() as cursor:
                insert_query = """
                    INSERT INTO stock_adjust_factor 
                    (stock_code, adjust_date, fore_adjust_factor, back_adjust_factor)
                    VALUES
                """
                
                values = []
                for row in rows:
                    values.append((
                        row['code'],
                        row['adjust_date'],
                        float(row['fore_adjust_factor']) if row['fore_adjust_factor'] is not None else 1.0,
                        float(row['back_adjust_factor']) if row['back_adjust_factor'] is not None else 1.0
                    ))
                
                await cursor.execute(insert_query, values)

    def _validate_kline_row(self, row: dict) -> tuple[bool, str]:
        """
        校验单条 K 线数据有效性
        
        P1 改进: 防止错误数据覆盖 ClickHouse
        """
        # 必填字段检查
        required = ['code', 'trade_date', 'open', 'close', 'volume']
        for field in required:
            if field not in row or row[field] is None:
                return False, f"缺少必填字段: {field}"
        
        # 价格合理性检查 (0 < price < 100000)
        for price_field in ['open', 'high', 'low', 'close']:
            val = row.get(price_field)
            if val is not None:
                try:
                    price = float(val)
                    if price < 0 or price > 100000:
                        return False, f"价格异常 ({price_field}={price})"
                except (ValueError, TypeError):
                    return False, f"价格格式错误 ({price_field}={val})"
        
        # OHLC 逻辑检查
        try:
            if row.get('high') and row.get('low'):
                high = float(row['high'])
                low = float(row['low'])
                if high < low:
                    return False, f"最高价({high}) < 最低价({low})"
        except (ValueError, TypeError):
            pass  # 如果转换失败，跳过逻辑检查
        
        # 成交量合理性检查
        try:
            volume = float(row['volume'])
            if volume < 0:
                return False, f"成交量为负数 ({volume})"
        except (ValueError, TypeError):
            return False, f"成交量格式错误 ({row['volume']})"
        
        return True, ""

    async def _insert_to_clickhouse(self, rows: list):
        """
        批量插入数据到 ClickHouse
        
        P1 改进: 插入前进行数据校验
        """
        if not rows:
            return
        
        # 数据校验
        valid_rows = []
        invalid_count = 0
        
        for row in rows:
            is_valid, error = self._validate_kline_row(row)
            if is_valid:
                valid_rows.append(row)
            else:
                invalid_count += 1
                logger.warning(
                    f"数据校验失败: {row.get('code')} {row.get('trade_date')} - {error}"
                )
        
        if invalid_count > 0:
            logger.warning(f"本批次 {invalid_count}/{len(rows)} 条数据未通过校验")
        
        if not valid_rows:
            logger.warning("批次中无有效数据，跳过插入")
            return
        
        # 执行插入
        async with self.clickhouse_pool.acquire() as ch_conn:
            async with ch_conn.cursor() as cursor:
                insert_query = """
                    INSERT INTO stock_kline_daily 
                    (stock_code, trade_date, open_price, high_price, low_price, 
                     close_price, volume, amount, turnover_rate, change_pct)
                    VALUES
                """
                
                values = []
                for row in valid_rows:
                    values.append((
                        row['code'],
                        row['trade_date'],
                        float(row['open']) if row['open'] is not None else 0.0,
                        float(row['high']) if row['high'] is not None else 0.0,
                        float(row['low']) if row['low'] is not None else 0.0,
                        float(row['close']) if row['close'] is not None else 0.0,
                        int(float(row['volume'])) if row['volume'] is not None else 0,
                        float(row['amount']) if row['amount'] is not None else 0.0,
                        float(row.get('turnover')) if row.get('turnover') is not None else None,
                        float(row.get('pct_chg')) if row.get('pct_chg') is not None else None
                    ))
                
                await cursor.execute("SET max_partitions_per_insert_block = 10000")
                await cursor.execute(insert_query, values)
                logger.debug(f"插入 {len(valid_rows)} 条记录到ClickHouse (校验通过率: {len(valid_rows)}/{len(rows)})")

    async def verify_consistency(self, trade_date: str):
        """
        验证指定日期的数据一致性 (Verify-After-Write)
        
        策略: 对比 MySQL 和 ClickHouse 的记录数
        """
        logger.info(f"正在校验数据一致性: {trade_date}")
        
        # 1. Query MySQL Count
        mysql_count = 0
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT COUNT(*) FROM stock_kline_daily WHERE trade_date = %s", (trade_date,))
                res = await cursor.fetchone()
                mysql_count = res[0] if res else 0

        # 2. Query ClickHouse Count
        ch_count = 0
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Use parameterized query to prevent SQL injection
                await cursor.execute("SELECT count() FROM stock_kline_daily WHERE trade_date = %(date)s", {'date': trade_date})
                res = await cursor.fetchone()
                ch_count = res[0] if res else 0
        
        # 3. Compare
        if mysql_count != ch_count:
            msg = f"数据不一致 ({trade_date}): MySQL={mysql_count} vs ClickHouse={ch_count}"
            logger.error(f"❌ {msg}")
            # Raise exception to trigger retry or failure log
            raise DataMismatchException(msg, mysql_count, ch_count)
        
        logger.info(f"✓ 一致性校验通过 ({trade_date}): count={mysql_count}")

    # ========== 增强验证层 (L2, L5, L7) ==========
    
    def _validate_price_continuity(self, current_row: dict, prev_row: dict) -> tuple[bool, str]:
        """
        L2: 历史一致性检查 - 检测价格异常跳变
        
        验证规则:
        - 单日涨跌幅不超过 ±30% (允许涨跌停、停牌复牌等特殊情况)
        """
        if not prev_row:
            return True, ""  # 第一条数据无法对比
        
        try:
            prev_close = float(prev_row['close'])
            curr_open = float(current_row['open'])
            curr_close = float(current_row['close'])
            
            if prev_close <= 0:
                return True, ""  # 前收盘价无效，跳过
            
            # 计算开盘价相对于前收盘价的变化
            open_change_pct = abs((curr_open - prev_close) / prev_close) * 100
            if open_change_pct > 30:
                return False, f"L2-开盘价异常跳变 {open_change_pct:.1f}% (前收:{prev_close}, 今开:{curr_open})"
            
            # 计算收盘价相对于前收盘价的变化
            close_change_pct = abs((curr_close - prev_close) / prev_close) * 100
            if close_change_pct > 30:
                return False, f"L2-收盘价异常跳变 {close_change_pct:.1f}% (前收:{prev_close}, 今收:{curr_close})"
            
            return True, ""
        except (ValueError, ZeroDivisionError, KeyError, TypeError):
            return True, ""  # 数据不足，跳过检查

    def _validate_cross_field_correlation(self, row: dict) -> tuple[bool, str]:
        """
        L5: 跨字段关联验证 - 检测字段间的数学关系
        
        验证规则:
        1. OHLC 增强: open/close 应在 [low, high] 范围内
        2. 成交额验证: amount ≈ 均价 × volume (允许 50% 误差)
        3. 换手率合理性: 0 <= turnover_rate <= 100
        """
        try:
            # 规则 1: OHLC 完整性
            open_price = float(row['open'])
            high = float(row['high'])
            low = float(row['low'])
            close = float(row['close'])
            
            if not (low <= open_price <= high):
                return False, f"L5-开盘价({open_price})不在[{low}, {high}]范围内"
            
            if not (low <= close <= high):
                return False, f"L5-收盘价({close})不在[{low}, {high}]范围内"
            
            # 规则 2: 成交额与价量关系 (放宽到 50% 误差)
            if row.get('amount') and row.get('volume'):
                amount = float(row['amount'])
                volume = float(row['volume'])
                
                if volume > 0 and amount > 0:
                    avg_price = (open_price + close) / 2
                    expected_amount = avg_price * volume
                    
                    if expected_amount > 0:
                        deviation = abs(amount - expected_amount) / expected_amount
                        if deviation > 0.5:  # 50% 误差阈值
                            return False, f"L5-成交额异常 (实际={amount:.0f}, 预期={expected_amount:.0f}, 偏差={deviation*100:.1f}%)"
            
            # 规则 3: 换手率合理性
            if row.get('turnover'):
                turnover_rate = float(row['turnover'])
                if turnover_rate < 0 or turnover_rate > 100:
                    return False, f"L5-换手率异常 ({turnover_rate}%)"
            
            return True, ""
        except (ValueError, ZeroDivisionError, KeyError, TypeError):
            return True, ""  # 数据不足或格式错误，跳过

    def _validate_batch_integrity(self, rows: list) -> tuple[bool, list]:
        """
        L7: 批次完整性验证 - 检查批次级别的数据质量
        
        验证规则:
        1. 批次内不应有重复的 (股票代码, 交易日期)
        2. 返回去重后的数据
        
        Returns:
            (is_valid, deduplicated_rows or error_messages)
        """
        if not rows:
            return True, []
        
        # 检查重复并去重
        seen = set()
        unique_rows = []
        duplicate_count = 0
        
        for row in rows:
            key = (row.get('code'), str(row.get('trade_date')))
            if key in seen:
                duplicate_count += 1
                logger.warning(f"L7-发现重复数据: {key}")
            else:
                seen.add(key)
                unique_rows.append(row)
        
        if duplicate_count > 0:
            logger.warning(f"L7-批次内发现 {duplicate_count} 条重复数据，已自动去重")
        
        return True, unique_rows

    async def _insert_to_clickhouse_enhanced(self, rows: list):
        """
        增强版批量插入（包含 L2, L5, L7 验证）
        
        验证流程:
        1. L7: 批次完整性（去重）
        2. L1: 基础合法性
        3. L5: 跨字段关联
        4. L2: 历史一致性（同股票连续数据）
        """
        if not rows:
            return
        
        validation_stats = {
            "total": len(rows),
            "L1_failed": 0,
            "L2_failed": 0,
            "L5_failed": 0,
            "L7_duplicates": 0,
        }
        
        # L7: 批次完整性（去重）
        _, unique_rows = self._validate_batch_integrity(rows)
        validation_stats["L7_duplicates"] = len(rows) - len(unique_rows)
        
        # 按股票代码分组，便于 L2 验证
        stock_groups = defaultdict(list)
        for row in unique_rows:
            stock_groups[row.get('code')].append(row)
        
        # 对每组按日期排序
        for code in stock_groups:
            stock_groups[code].sort(key=lambda x: str(x.get('trade_date', '')))
        
        valid_rows = []
        
        for code, group_rows in stock_groups.items():
            prev_row = None
            for row in group_rows:
                # L1: 基础验证
                is_valid, error = self._validate_kline_row(row)
                if not is_valid:
                    validation_stats["L1_failed"] += 1
                    logger.warning(f"L1验证失败: {code} {row.get('trade_date')} - {error}")
                    continue
                
                # L5: 跨字段关联 (指数代码跳过由于成交量计算差异导致的校验失败)
                # 兼容多种格式: sh.000001, 000001.SH, 399001.SZ
                is_index = code.startswith(('sh.000', 'sz.399', '000', '399')) or code.endswith(('.SH', '.SZ')) and (code.startswith('000') or code.startswith('399'))
                if not is_index:
                    is_valid, error = self._validate_cross_field_correlation(row)
                    if not is_valid:
                        validation_stats["L5_failed"] += 1
                        logger.warning(f"L5验证失败: {code} {row.get('trade_date')} - {error}")
                        continue
                
                # L2: 历史一致性
                is_valid, error = self._validate_price_continuity(row, prev_row)
                if not is_valid:
                    validation_stats["L2_failed"] += 1
                    logger.warning(f"L2验证失败: {code} {row.get('trade_date')} - {error}")
                    # L2 失败不跳过，只记录警告（因为可能是正常的停牌复牌）
                
                valid_rows.append(row)
                prev_row = row
        
        # 统计日志
        pass_rate = (len(valid_rows) / len(rows) * 100) if rows else 0
        logger.info(f"增强验证统计: {validation_stats}, 通过率: {pass_rate:.1f}%")
        
        if not valid_rows:
            logger.warning("增强验证后无有效数据，跳过插入")
            return
        
        # 执行插入
        async with self.clickhouse_pool.acquire() as ch_conn:
            async with ch_conn.cursor() as cursor:
                insert_query = """
                    INSERT INTO stock_kline_daily 
                    (stock_code, trade_date, open_price, high_price, low_price, 
                     close_price, volume, amount, turnover_rate, change_pct)
                    VALUES
                """
                
                values = []
                for row in valid_rows:
                    values.append((
                        row['code'],
                        row['trade_date'],
                        float(row['open']) if row['open'] is not None else 0.0,
                        float(row['high']) if row['high'] is not None else 0.0,
                        float(row['low']) if row['low'] is not None else 0.0,
                        float(row['close']) if row['close'] is not None else 0.0,
                        int(float(row['volume'])) if row['volume'] is not None else 0,
                        float(row['amount']) if row['amount'] is not None else 0.0,
                        float(row.get('turnover')) if row.get('turnover') is not None else None,
                        float(row.get('pct_chg')) if row.get('pct_chg') is not None else None
                    ))
                
                await cursor.execute("SET max_partitions_per_insert_block = 10000")
                await cursor.execute(insert_query, values)
                logger.info(f"✓ 插入 {len(valid_rows)} 条记录到ClickHouse (增强验证通过率: {pass_rate:.1f}%)")




"""
K线数据同步核心服务
"""
import asyncio
import aiomysql
import asynch
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

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

    async def _log_to_db(self, status: str, records: int, message: str, duration: float):
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
                        "kline_daily_sync", 
                        status.upper(), 
                        records, 
                        message, 
                        duration
                    ))
                    await conn.commit()
            logger.info("✓ 执行日志已写入 MySQL")
        except Exception as e:
            logger.error(f"写入执行日志失败: {e}")

    async def sync_full(self, batch_size: int = 10000):
        """
        全量同步：从MySQL同步所有K线数据到ClickHouse
        Args:
            batch_size: 每批次同步的记录数
        """
        logger.info("开始全量同步...")
        await self._update_status("running", "开始全量同步...", 0.0)
        
        try:
            async with self.mysql_pool.acquire() as mysql_conn:
                async with mysql_conn.cursor(aiomysql.DictCursor) as cursor:
                    # 查询总记录数
                    await cursor.execute("SELECT COUNT(*) as cnt FROM stock_kline_daily")
                    total = (await cursor.fetchone())['cnt']
                    logger.info(f"MySQL总记录数: {total:,}")
                    
                    # 分批读取并写入
                    offset = 0
                    synced = 0
                    
                    while offset < total:
                        query = f"""
                            SELECT 
                                code, trade_date, open, high, low, close,
                                volume, amount, turnover, pct_chg
                            FROM stock_kline_daily
                            ORDER BY trade_date, code
                            LIMIT {batch_size} OFFSET {offset}
                        """
                        
                        await cursor.execute(query)
                        rows = await cursor.fetchall()
                        
                        if not rows:
                            break
                        
                        # 写入ClickHouse
                        await self._insert_to_clickhouse(rows)
                        
                        synced += len(rows)
                        offset += batch_size
                        
                        progress = min(99.9, (synced / total) * 100)
                        logger.info(f"进度: {synced:,}/{total:,} ({progress:.1f}%)")
                        await self._update_status("running", f"同步中: {synced:,}/{total:,}", progress)
                    
                    logger.info(f"✓ 全量同步完成，共同步 {synced:,} 条记录")
                    await self._update_status("success", f"全量同步完成，共 {synced:,} 条", 100.0, {"total_synced": synced})

        except Exception as e:
            await self._update_status("failed", f"全量同步失败: {str(e)}", 0.0)
            raise e
    
    async def sync_smart_incremental(self):
        """
        智能增量同步：基于ClickHouse最大日期自动同步新数据
        """
        start_time = datetime.now()
        logger.info("开始智能增量同步...")
        await self._update_status("running", "正在检查新数据...", 0.0)
        
        try:
            # 第1步：查询ClickHouse中的最大交易日期
            async with self.clickhouse_pool.acquire() as ch_conn:
                async with ch_conn.cursor() as cursor:
                    query = "SELECT MAX(trade_date) as max_date FROM stock_kline_daily"
                    await cursor.execute(query)
                    result = await cursor.fetchone()
                    ch_max_date = result[0] if result and result[0] else None
            
            if ch_max_date:
                logger.info(f"ClickHouse最大日期: {ch_max_date}")
            else:
                logger.warning("ClickHouse表为空，将执行全量同步")
                await self.sync_full()
                return
            
            # 第2步：从MySQL查询大于此日期的数据
            async with self.mysql_pool.acquire() as mysql_conn:
                async with mysql_conn.cursor(aiomysql.DictCursor) as cursor:
                    query = """
                        SELECT 
                            code, trade_date, open, high, low, close,
                            volume, amount, turnover, pct_chg
                        FROM stock_kline_daily
                        WHERE trade_date > %s
                        ORDER BY trade_date, code
                    """
                    
                    await cursor.execute(query, (ch_max_date,))
                    rows = await cursor.fetchall()
            
            # 第3步：同步新数据
            duration = (datetime.now() - start_time).total_seconds()
            if rows:
                await self._insert_to_clickhouse(rows)
                min_date = min(row['trade_date'] for row in rows)
                max_date = max(row['trade_date'] for row in rows)
                msg = f"智能增量同步完成：{len(rows):,} 条记录 ({min_date} ~ {max_date})"
                logger.info(f"✓ {msg}")
                await self._update_status("success", msg, 100.0, {"new_records": len(rows), "date_range": f"{min_date}~{max_date}"})
                await self._log_to_db("SUCCESS", len(rows), msg, duration)
            else:
                msg = "无新数据需要同步，ClickHouse已是最新状态"
                logger.info(f"✓ {msg}")
                await self._update_status("success", msg, 100.0, {
                    "new_records": 0,
                    "date": datetime.now().strftime('%Y-%m-%d')
                })
                await self._log_to_db("SUCCESS", 0, msg, duration)

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            await self._update_status("failed", f"智能同步失败: {str(e)}", 0.0)
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
            async with self.mysql_pool.acquire() as mysql_conn:
                async with mysql_conn.cursor(aiomysql.DictCursor) as cursor:
                    # 1. 获取总数
                    await cursor.execute("SELECT COUNT(*) as cnt FROM stock_adjust_factor")
                    total = (await cursor.fetchone())['cnt']
                    logger.info(f"MySQL 复权因子总数: {total:,}")
                    
                    if total == 0:
                        await self._update_status("success", "MySQL无复权因子数据", 100.0)
                        return

                    # 2. 分批同步
                    offset = 0
                    synced = 0
                    while offset < total:
                        query = f"""
                            SELECT code, adjust_date, fore_adjust_factor, back_adjust_factor
                            FROM stock_adjust_factor
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

    async def _insert_factors_to_clickhouse(self, rows: list):
        """批量插入复权因子到 ClickHouse"""
        if not rows:
            return
        
        async with self.clickhouse_pool.acquire() as ch_conn:
            async with ch_conn.cursor() as cursor:
                insert_query = """
                    INSERT INTO stock_adjust_factor 
                    (stock_code, ex_date, fore_factor, back_factor)
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

    async def _insert_to_clickhouse(self, rows: list):
        """批量插入数据到ClickHouse"""
        if not rows:
            return
        
        async with self.clickhouse_pool.acquire() as ch_conn:
            async with ch_conn.cursor() as cursor:
                insert_query = """
                    INSERT INTO stock_kline_daily 
                    (stock_code, trade_date, open_price, high_price, low_price, 
                     close_price, volume, amount, turnover_rate, change_pct)
                    VALUES
                """
                
                values = []
                for row in rows:
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
                logger.debug(f"插入 {len(rows)} 条记录到ClickHouse")

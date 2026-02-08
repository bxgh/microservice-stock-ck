"""
Metadata 同步服务
负责将 MySQL 中的辅助表（股东、估值、大宗等）同步至 ClickHouse
"""
import asyncio
import aiomysql
import asynch
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class MetadataSyncService:
    """Metadata 同步服务"""
    
    def __init__(self):
        self.mysql_pool = None
        self.clickhouse_pool = None
        self.cluster_name = os.getenv('CLICKHOUSE_CLUSTER', 'stock_cluster')
        
        # 表映射关系 (已根据真实 Schema 校准)
        self.table_map = {
            'stock_shareholder_count': {
                'clickhouse': 'stock_holder_count',
                'date_col': 'end_date',
                'mysql_cols': ['ts_code', 'end_date', 'holder_count', 'holder_change_pct', 'avg_market_cap', 'updated_at'],
                'ch_cols': ['stock_code', 'report_date', 'holder_count', 'change', 'avg_market_cap', 'update_time']
            },
            'stock_top10_shareholders': {
                'clickhouse': 'stock_top_holders',
                'date_col': 'end_date',
                'mysql_cols': ['ts_code', 'end_date', 'rank', 'holder_name', 'hold_count', 'hold_pct', 'share_type', 'updated_at'],
                'ch_cols': ['stock_code', 'report_date', 'rank', 'holder_name', 'hold_count', 'hold_pct', 'share_type', 'update_time']
            },
            'daily_basic': {
                'clickhouse': 'stock_valuation',
                'date_col': 'trade_date',
                'mysql_cols': ['ts_code', 'trade_date', 'pe', 'pb', 'ps', 'total_mv', 'close'],
                'ch_cols': ['stock_code', 'trade_date', 'pe', 'pb', 'ps', 'market_cap', 'price']
            },
            'stock_block_trade': {
                'clickhouse': 'stock_block_trade',
                'date_col': 'trade_date',
                'mysql_cols': ['ts_code', 'trade_date', 'price', 'volume', 'amount', 'buyer', 'seller', 'updated_at'],
                'ch_cols': ['stock_code', 'trade_date', 'price', 'volume', 'amount', 'buyer', 'seller', 'update_time']
            },
            'stock_lhb_daily': {
                'clickhouse': 'stock_top_list',
                'date_col': 'trade_date',
                'mysql_cols': ['ts_code', 'trade_date', 'reason', 'net_buy_amt', 'turnover_rate', 'close_price', 'change_pct', 'updated_at'],
                'ch_cols': ['stock_code', 'trade_date', 'reason', 'net_buy', 'turnover_rate', 'close_price', 'change_pct', 'update_time']
            },
            'stock_sector_cons_ths': {
                'clickhouse': 'stock_sector_cons_ths',
                'date_col': 'updated_at',
                'mysql_cols': ['ts_code', 'sector_id', 'updated_at'],
                'ch_cols': ['stock_code', 'sector_id', 'update_time']
            },
            'stock_restricted_release': {
                'clickhouse': 'stock_restricted_release',
                'date_col': 'release_date',
                'mysql_cols': ['ts_code', 'release_date', 'release_count', 'release_market_cap', 'ratio', 'holder_type', 'updated_at'],
                'ch_cols': ['stock_code', 'release_date', 'release_count', 'release_market_cap', 'ratio', 'holder_type', 'update_time']
            },
            'stock_north_funds_daily': {
                'clickhouse': 'stock_north_funds_daily',
                'date_col': 'trade_date',
                'mysql_cols': ['ts_code', 'trade_date', 'hold_count', 'hold_market_cap', 'hold_ratio', 'updated_at'],
                'ch_cols': ['stock_code', 'trade_date', 'hold_count', 'hold_market_cap', 'hold_ratio', 'update_time']
            },
            'stock_analyst_rank': {
                'clickhouse': 'stock_analyst_rank',
                'date_col': 'report_date',
                'mysql_cols': ['stock_code', 'report_date', 'analyst', 'rating', 'change_direction', 'target_price', 'created_at'],
                'ch_cols': ['stock_code', 'report_date', 'analyst', 'rating', 'change_direction', 'target_price', 'update_time']
            },
            'stock_performance_forecast': {
                'clickhouse': 'stock_performance_forecast',
                'date_col': 'report_period',
                'mysql_cols': ['ts_code', 'report_period', 'notice_date', 'type', 'growth_range', 'updated_at'],
                'ch_cols': ['stock_code', 'report_period', 'notice_date', 'type', 'growth_range', 'update_time']
            },
            'stock_sentiment_daily': {
                'clickhouse': 'stock_sentiment_daily',
                'date_col': 'trade_date',
                'mysql_cols': ['stock_code', 'trade_date', 'post_count', 'read_count', 'comment_count', 'rank_score'],
                'ch_cols': ['stock_code', 'trade_date', 'post_count', 'read_count', 'comment_count', 'rank_score']
            },
            'stock_suspensions': {
                'clickhouse': 'stock_suspensions',
                'date_col': 'trade_date',
                'mysql_cols': ['ts_code', 'trade_date', 'is_suspended', 'reason', 'updated_at'],
                'ch_cols': ['stock_code', 'trade_date', 'is_suspended', 'reason', 'update_time']
            },
            'stock_xr_schedules': {
                'clickhouse': 'stock_xr_schedules',
                'date_col': 'ex_date',
                'mysql_cols': ['ts_code', 'ex_date', 'bonus_ratio', 'cash_div', 'created_at'],
                'ch_cols': ['stock_code', 'ex_date', 'bonus_ratio', 'cash_div', 'update_time']
            },
            'stock_industry_sw': {
                'clickhouse': 'stock_industry_sw',
                'date_col': 'update_time',
                'mysql_cols': ['code', 'l1_code', 'l1_name', 'l2_code', 'l2_name', 'l3_code', 'l3_name', 'update_time'],
                'ch_cols': ['stock_code', 'l1_code', 'l1_name', 'l2_code', 'l2_name', 'l3_code', 'l3_name', 'update_time']
            },
            'stock_industry_ths': {
                'clickhouse': 'stock_industry_ths',
                'date_col': 'updated_at',
                'mysql_cols': ['ts_code', 'l1_name', 'l2_name', 'l3_name', 'updated_at'],
                'ch_cols': ['stock_code', 'l1_name', 'l2_name', 'l3_name', 'update_time']
            },
            'stock_sector_ths': {
                'clickhouse': 'stock_sector_ths',
                'date_col': 'updated_at',
                'mysql_cols': ['id', 'sector_name', 'sector_type', 'sector_level', 'updated_at'],
                'ch_cols': ['sector_id', 'sector_name', 'sector_type', 'sector_level', 'update_time']
            },
            'stock_industry_em': {
                'clickhouse': 'stock_industry_em',
                'date_col': 'updated_at',
                'mysql_cols': ['ts_code', 'industry_code', 'industry_name', 'updated_at'],
                'ch_cols': ['stock_code', 'industry_code', 'industry_name', 'update_time']
            },
            'stock_basic_info': {
                'clickhouse': 'stock_basic_info',
                'date_col': 'list_date',
                'mysql_cols': ['ts_code', 'symbol', 'name', 'area', 'industry', 'fullname', 'enname', 'cnspell', 'market', 'exchange', 'curr_type', 'list_status', 'list_date', 'delist_date', 'is_hs', 'act_name', 'act_ent_type', 'issue_price'],
                'ch_cols': ['stock_code', 'symbol', 'name', 'area', 'industry', 'fullname', 'enname', 'cnspell', 'market', 'exchange', 'curr_type', 'list_status', 'list_date', 'delist_date', 'is_hs', 'act_name', 'act_ent_type', 'issue_price']
            },
            'trade_cal': {
                'clickhouse': 'stock_trade_cal',
                'date_col': 'cal_date',
                'mysql_cols': ['cal_date', 'exchange', 'is_open', 'pretrade_date'],
                'ch_cols': ['cal_date', 'exchange', 'is_open', 'pretrade_date']
            },
            'stock_adjust_factor': {
                'clickhouse': 'stock_adjust_factor',
                'date_col': 'adjust_date',
                'mysql_cols': ['code', 'adjust_date', 'fore_adjust_factor', 'back_adjust_factor', 'adjust_factor'],
                'ch_cols': ['stock_code', 'adjust_date', 'fore_adjust_factor', 'back_adjust_factor', 'adjust_factor']
            },
            'ts_concept_detail': {
                'clickhouse': 'stock_concept_detail',
                'date_col': 'in_date',
                'mysql_cols': ['concept_name', 'ts_code', 'name', 'in_date', 'out_date'],
                'ch_cols': ['concept_name', 'stock_code', 'name', 'in_date', 'out_date']
            }
        }

    async def initialize(self):
        """初始化连接池"""
        db_host = os.getenv('MYSQL_HOST', '127.0.0.1')
        db_port = int(os.getenv('MYSQL_PORT', 3306))
        db_user = os.getenv('MYSQL_USER', 'root')
        db_password = os.getenv('MYSQL_PASSWORD', '')
        db_name = os.getenv('MYSQL_DATABASE', 'alwaysup')

        # 兼容性环境变量
        if os.getenv('GSD_DB_HOST'):
            db_host = os.getenv('GSD_DB_HOST')
            db_port = int(os.getenv('GSD_DB_PORT', 3306))
            db_user = os.getenv('GSD_DB_USER', 'root')
            db_password = os.getenv('GSD_DB_PASSWORD', '')
            db_name = os.getenv('GSD_DB_NAME', 'alwaysup')

        self.mysql_pool = await aiomysql.create_pool(
            host=db_host, port=db_port, user=db_user, password=db_password, db=db_name,
            charset='utf8mb4', minsize=1, maxsize=5
        )
        
        self.clickhouse_pool = await asynch.create_pool(
            host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
            port=int(os.getenv('CLICKHOUSE_PORT', 9000)),
            user=os.getenv('CLICKHOUSE_USER', 'admin'),
            password=os.getenv('CLICKHOUSE_PASSWORD', 'admin123'),
            database=os.getenv('CLICKHOUSE_DB', 'stock_data')
        )
        logger.info(f"MetadataSyncService initialized with MySQL ({db_host}:{db_port}) and ClickHouse")

    async def close(self):
        """关闭连接池"""
        if self.mysql_pool:
            self.mysql_pool.close()
            await self.mysql_pool.wait_closed()
        if self.clickhouse_pool:
            self.clickhouse_pool.close()
            await self.clickhouse_pool.wait_closed()

    async def sync_table(self, mysql_table: str, days: int = 7) -> int:
        """同步单个表"""
        if mysql_table not in self.table_map:
            logger.error(f"Table {mysql_table} not in sync map")
            return 0
            
        config = self.table_map[mysql_table]
        ch_table = config['clickhouse']
        date_col = config['date_col']
        mysql_cols = config['mysql_cols']
        ch_cols = config['ch_cols']
        
        logger.info(f"Starting sync for {mysql_table} -> {ch_table} (Lookback: {days} days)")
        
        # 1. 确定增量同步的时间范围
        # 使用 Asia/Shanghai 时区
        tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 2. 从 MySQL 获取数据
        cols_str = ', '.join(mysql_cols)
        if days >= 0:
            query = f"SELECT {cols_str} FROM {mysql_table} WHERE {date_col} >= %s"
            params = (start_date,)
        else:
            query = f"SELECT {cols_str} FROM {mysql_table}"
            params = ()
        
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                rows = await cursor.fetchall()
        
        if not rows:
            logger.info(f"No new data for {mysql_table} since {start_date}")
            return 0

        # 3. 尝试清理 ClickHouse 中对应日期的数据 (非必须，因为是 ReplacingMergeTree)
        unique_dates = sorted(list(set(row[mysql_cols.index(date_col)] for row in rows if row[mysql_cols.index(date_col)] is not None)))
        
        # 优化：如果日期太多（超过 50 个），说明是全量或大规模同步，使用一次性 DELETE 或跳过
        if len(unique_dates) > 0 and len(unique_dates) <= 50:
            for d in unique_dates:
                d_str = d.strftime('%Y-%m-%d') if isinstance(d, datetime) else str(d)
                if '-' not in d_str: # YYYYMMDD -> YYYY-MM-DD
                    d_str = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                    
                try:
                    async with self.clickhouse_pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            date_ch_col = config['ch_cols'][config['mysql_cols'].index(date_col)]
                            await cursor.execute(
                                f"ALTER TABLE {ch_table}_local ON CLUSTER {self.cluster_name} DELETE WHERE {date_ch_col} = %(d)s",
                                {'d': d_str}
                            )
                except Exception as e:
                    logger.warning(f"Failed to delete partition for {ch_table} on date {d_str} (non-fatal): {e}")
        elif len(unique_dates) > 50:
            logger.info(f"Large batch detected ({len(unique_dates)} dates). Skipping granular DELETE to avoid mutation overhead.")
        
        # 4. 插入到 ClickHouse
        # 如果 ClickHouse 表定义中有 update_time，且 mysql_cols 中没有，我们让 ClickHouse 自动生成 now()
        # 已经在 ClickHouse 侧通过 DEFAULT now() 处理了
        insert_cols = ', '.join(ch_cols)
        insert_query = f"INSERT INTO {ch_table} ({insert_cols}) VALUES"
        
        # 转换数据格式
        values = []
        for index, row in enumerate(rows):
            processed_row = []
            try:
                for i, val in enumerate(row):
                    ch_col = ch_cols[i]
                    if val is None:
                        # 对于 DDL 中定义为 Nullable 的字段，保持 None
                        if any(suffix in ch_col for suffix in ['date', 'time', 'price', 'factor', 'ratio', 'count', 'amount']):
                            processed_row.append(None)
                        else:
                            processed_row.append("")
                    elif isinstance(val, (datetime, timedelta)):
                        processed_row.append(str(val))
                    elif any(suffix in ch_col for suffix in ['price', 'factor', 'ratio', 'count', 'amount']):
                        # 强制转为 float，确保 numeric 类型一致性
                        try:
                            if val is None:
                                processed_row.append(None)
                            else:
                                f_val = float(val)
                                import math
                                if math.isnan(f_val) or math.isinf(f_val):
                                    processed_row.append(None)
                                else:
                                    processed_row.append(f_val)
                        except:
                            processed_row.append(None)
                    else:
                        processed_row.append(val)
                values.append(tuple(processed_row))
            except Exception as e:
                logger.error(f"Failed to process row {index}: {row}, error: {e}")
                continue

        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 设置超时和相关设置
                await cursor.execute("SET insert_distributed_sync = 1") # 同步写入分布式表
                await cursor.execute(insert_query, values)
        
        logger.info(f"Successfully synced {len(rows)} records for {mysql_table}")
        return len(rows)

    async def sync_all(self, days: int = 7) -> Dict[str, int]:
        """同步所有映射的表"""
        results = {}
        for mysql_table in self.table_map.keys():
            try:
                count = await self.sync_table(mysql_table, days)
                results[mysql_table] = count
            except Exception as e:
                logger.error(f"Failed to sync {mysql_table}: {e}")
                results[mysql_table] = -1
        return results

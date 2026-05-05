
import asyncio
import logging
import os
import json
import time
from typing import List, Dict
import aiomysql
from clickhouse_driver import Client as ClickHouseClient

from gsd_shared.redis_protocol import (
    RedisStreamClient, TickJob, TickResult, JobType, JobStatus,
    STREAM_KEY_JOBS, STREAM_KEY_DATA, GROUP_MOOTDX_WORKERS
)

logger = logging.getLogger("stream-adapter")

class JobPublisher:
    """
    任务发布器
    负责从数据库读取股票列表，并生成每日采集任务推送到 Redis Stream
    """
    def __init__(self):
        # MySQL Config
        self.mysql_host = os.getenv("GSD_DB_HOST", "127.0.0.1")
        self.mysql_port = int(os.getenv("GSD_DB_PORT", 36301))
        self.mysql_user = os.getenv("GSD_DB_USER", "root")
        self.mysql_password = os.getenv("GSD_DB_PASSWORD", "alwaysup@888")
        self.mysql_db = os.getenv("GSD_DB_NAME", "alwaysup")
        
        # Redis
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = os.getenv("REDIS_PORT", 6379)
        redis_password = os.getenv("REDIS_PASSWORD", "")
        auth_part = f":{redis_password}@" if redis_password else ""
        redis_url = f"redis://{auth_part}{redis_host}:{redis_port}/0"
        is_cluster = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
        
        self.redis_client = RedisStreamClient(redis_url, is_cluster=is_cluster)

    async def publish_daily_jobs(self, date_str: str, job_type: JobType = JobType.POST_MARKET):
        """
        发布全量任务
        """
        logger.info(f"Starting to publish jobs for {date_str} (Type: {job_type})")
        
        try:
            # 1. Get Stock List from MySQL
            pool = await aiomysql.create_pool(
                host=self.mysql_host, port=self.mysql_port,
                user=self.mysql_user, password=self.mysql_password,
                db=self.mysql_db, cursorclass=aiomysql.DictCursor
            )
            
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 优先从 stock_basic 获取，如果没有则尝试从 stock_kline_daily 获取最近活跃的
                    try:
                        await cur.execute("SELECT symbol as code, market FROM stock_basic WHERE status=1") # Assuming table structure
                        rows = await cur.fetchall()
                        if not rows:
                             # Fallback
                             logger.warning("stock_basic empty or missing, falling back to recent stocks")
                             await cur.execute("SELECT DISTINCT code FROM stock_kline_daily WHERE trade_date > DATE_SUB(NOW(), INTERVAL 30 DAY)")
                             rows = await cur.fetchall()
                    except Exception as db_e:
                        logger.warning(f"Failed to query stock_basic: {db_e}, trying fallback")
                        await cur.execute("SELECT DISTINCT code FROM stock_kline_daily ORDER BY code")
                        rows = await cur.fetchall()
            
            pool.close()
            await pool.wait_closed()
            
            if not rows:
                logger.error("No stocks found to process!")
                return
                
            logger.info(f"Found {len(rows)} stocks. Publishing to Redis...")
            
            # 2. Publish to Redis
            count = 0
            pipe = self.redis_client.redis.pipeline()
            
            for row in rows:
                code = row['code']
                # Generate Job ID
                import uuid
                job_id = str(uuid.uuid4())
                
                job = TickJob(
                    job_id=job_id,
                    stock_code=code,
                    type=job_type,
                    date=date_str,
                    market=row.get('market')
                )
                
                # Batch add (Pipeline)
                # RedisStreamClient methods are async, usually single op. 
                # For high thru, we construct raw commands or loop await.
                # await in loop is fine for 5000 items (Redis is fast).
                await self.redis_client.publish_job(job)
                count += 1
                
                if count % 100 == 0:
                    logger.info(f"Published {count} jobs...")
            
            # Ensure consumer group (optional, idempotent)
            await self.redis_client.init_consumer_group(STREAM_KEY_JOBS, GROUP_MOOTDX_WORKERS)
            
            logger.info(f"✅ Successfully published {count} jobs for {date_str}")
            
        except Exception as e:
            logger.error(f"Failed to publish jobs: {e}")
            raise
        finally:
            await self.redis_client.aclose()


class BatchWriter:
    """
    批量入库器
    监听 stream:tick:data，缓冲并批量写入 ClickHouse
    """
    def __init__(self):
        # ClickHouse
        self.ch_host = os.getenv("CLICKHOUSE_HOST", "127.0.0.1")
        self.ch_port = int(os.getenv("CLICKHOUSE_PORT", 9000))
        self.ch_user = os.getenv("CLICKHOUSE_USER", "default")
        self.ch_password = os.getenv("CLICKHOUSE_PASSWORD", "")
        self.ch_db = os.getenv("CLICKHOUSE_DB", "stock_data")
        
        self.ch_client = ClickHouseClient(
            host=self.ch_host, port=self.ch_port,
            user=self.ch_user, password=self.ch_password,
            database=self.ch_db
        )
        
        # Redis
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = os.getenv("REDIS_PORT", 6379)
        redis_password = os.getenv("REDIS_PASSWORD", "")
        auth_part = f":{redis_password}@" if redis_password else ""
        redis_url = f"redis://{auth_part}{redis_host}:{redis_port}/0"
        is_cluster = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
        
        self.redis_client = RedisStreamClient(redis_url, is_cluster=is_cluster)
        self.group_name = "group:ck_writer"
        self.consumer_name = f"writer-{os.getpid()}"
        
        self.running = False
        self.buffer: List[Dict] = []
        self.buffer_size_limit = 20000 # Rows limit
        self.last_flush_time = time.time()
        self.flush_interval = 2.0 # Seconds

    async def start(self):
        logger.info("Starting Batch Writer...")
        self.running = True
        
        # Helper method for CK writer Consumer Group
        try:
             await self.redis_client.redis.xgroup_create(STREAM_KEY_DATA, self.group_name, id="0", mkstream=True)
        except Exception as e:
            pass # Ignore if exists
            
        while self.running:
            try:
                # 1. Read from Redis
                streams = await self.redis_client.redis.xreadgroup(
                    self.group_name, self.consumer_name,
                    {STREAM_KEY_DATA: ">"}, count=100, block=1000
                )
                
                # 2. Check flush conditions (Time based or Size based)
                current_time = time.time()
                time_diff = current_time - self.last_flush_time
                
                if streams:
                    for stream_key, messages in streams:
                        logger.info(f"Pulled {len(messages)} messages from {stream_key}")
                        for msg_id, msg_data in messages:
                            # Process: Parse -> Load JSON -> Flatten to rows -> Add to buffer
                            await self._process_msg(msg_id, msg_data)
                else:
                    # logger.debug("No new messages in stream")
                    pass
                
                # Check Flush
                if len(self.buffer) >= self.buffer_size_limit or (len(self.buffer) > 0 and time_diff > self.flush_interval):
                    await self._flush_buffer()
                    
            except Exception as e:
                logger.error(f"Writer loop error: {e}")
                await asyncio.sleep(1)

    async def _process_msg(self, msg_id, msg_data):
        try:
            # Pydantic Parse (Optional, using direct access for speed)
            status = msg_data.get('status')
            data_blob = msg_data.get('data_blob')
            stock_code = msg_data.get('stock_code')
            if status == JobStatus.SUCCESS or status == JobStatus.PARTIAL:
                if data_blob:
                    rows = json.loads(data_blob)
                    # logger.info(f"Processing {len(rows)} rows for {stock_code}")
                    for row in rows:
                        vol = int(row.get('vol', 0))
                        price = float(row.get('price', 0))
                        
                        raw_date = msg_data.get('date', '')
                        from datetime import datetime
                        try:
                            if len(raw_date) == 8:
                                trade_date = datetime.strptime(raw_date, "%Y%m%d").date()
                            else:
                                trade_date = datetime.now().date()
                        except:
                            trade_date = datetime.now().date()
                            
                        self.buffer.append({
                            'stock_code': stock_code,
                            'trade_date': trade_date,
                            'tick_time': row.get('time'),
                            'price': price,
                            'volume': vol,
                            'amount': price * vol,
                            'direction': int(row.get('direction', row.get('buyorsell', 2))) # Handle both field names
                        })
                else:
                    logger.debug(f"Msg {msg_id} for {stock_code} has no data_blob")
            else:
                logger.debug(f"Msg {msg_id} for {stock_code} has status {status}, skipping")
            
            # ACK immediately to prevent blocking
            await self.redis_client.redis.xack(STREAM_KEY_DATA, self.group_name, msg_id)
            
        except Exception as e:
            logger.error(f"Failed to process msg {msg_id}: {e}")
            await self.redis_client.redis.xack(STREAM_KEY_DATA, self.group_name, msg_id)

    async def _flush_buffer(self):
        if not self.buffer:
            return
            
        logger.info(f"Flushing {len(self.buffer)} rows to ClickHouse...")
        
        start_t = time.time()
        try:
            # ClickHouse batch insert
            self.ch_client.execute(
                f"INSERT INTO {self.ch_db}.tick_data (stock_code, trade_date, tick_time, price, volume, amount, direction) VALUES",
                self.buffer
            )
            
            self.buffer.clear()
            self.last_flush_time = time.time()
            logger.info(f"Flush Success. Took {time.time() - start_t:.3f}s")
            
        except Exception as e:
            logger.error(f"Flush to ClickHouse failed: {e}")
            # If failed, we clear buffer to avoid memory leak, but in production we might want to retry.
            # For QC, we keep it simple but logged.
            self.buffer.clear() 


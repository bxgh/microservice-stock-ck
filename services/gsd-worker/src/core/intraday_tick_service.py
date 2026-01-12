import asyncio
import aiohttp
import asynch
import os
import logging
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import pytz

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class IntradayTickService:
    """
    盘中分笔采集服务
    支持增量采集、递归回溯以及指纹去重
    """
    
    def __init__(self):
        self.logger = logging.getLogger("IntradayTickService")
        self.clickhouse_pool = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.mootdx_api_url = os.getenv("MOOTDX_API_URL", "http://127.0.0.1:8003")
        self.redis = None
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """初始化资源"""
        async with self._lock:
            # ClickHouse
            if self.clickhouse_pool is None:
                self.clickhouse_pool = await asynch.create_pool(
                    host=os.getenv("CLICKHOUSE_HOST", "127.0.0.1"),
                    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
                    database=os.getenv("CLICKHOUSE_DB", "stock_data"),
                    user=os.getenv("CLICKHOUSE_USER", "default"),
                    password=os.getenv("CLICKHOUSE_PASSWORD", ""),
                    minsize=1,
                    maxsize=10
                )
                logger.info("✓ ClickHouse pool initialized")
            
            # HTTP
            if self.http_session is None:
                timeout = aiohttp.ClientTimeout(total=30)
                self.http_session = aiohttp.ClientSession(timeout=timeout)
                logger.info(f"✓ HTTP session initialized: {self.mootdx_api_url}")

            # Redis (using standard redis.asyncio)
            if self.redis is None:
                import redis.asyncio as aioredis
                host = os.getenv("REDIS_HOST", "127.0.0.1")
                port = os.getenv("REDIS_PORT", "6379")
                password = os.getenv("REDIS_PASSWORD", "redis123")
                db = int(os.getenv("REDIS_DB", "0"))
                self.redis = aioredis.from_url(
                    f"redis://:{password}@{host}:{port}/{db}",
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("✓ Redis connection initialized")

    async def get_latest_ticks_from_db(self, stock_code: str, trade_date_str: str, limit: int = 500) -> List[str]:
        """
        获取数据库中最新的 N 条成交记录的指纹，用于去重和断层检测
        """
        try:
            async with self.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 使用 tick_time 排序。注意：tick_time 是 String "HH:MM:SS"
                    # 我们需要最近的记录
                    query = f"""
                        SELECT tick_time, price, volume, direction 
                        FROM tick_data_intraday_local 
                        WHERE stock_code = '{stock_code}' AND trade_date = '{trade_date_str}'
                        ORDER BY tick_time DESC, created_at DESC
                        LIMIT {limit}
                    """
                    await cursor.execute(query)
                    rows = await cursor.fetchall()
                    
                    # 生成指纹: (time, price, volume, direction)
                    fingerprints = [
                        self._gen_fingerprint(row[0], row[1], row[2], row[3])
                        for row in rows
                    ]
                    return fingerprints
        except Exception as e:
            logger.error(f"Failed to get existing ticks for {stock_code}: {e}")
            return []

    def _gen_fingerprint(self, time_str, price, volume, direction) -> str:
        """生成唯一成交指纹"""
        # 统一时间格式为 HH:MM:SS
        if len(str(time_str)) == 5:
            time_str = f"{time_str}:00"
        s = f"{time_str}|{float(price):.3f}|{int(volume)}|{int(direction)}"
        return hashlib.md5(s.encode()).hexdigest()

    async def fetch_batch(self, stock_code: str, date_int: int, start: int = 0, offset: int = 800) -> List[Dict]:
        """拉取一批数据"""
        # [Fix] Mootdx transaction() 需要明确的 market (sh/sz) 前缀才能正确获取实时数据
        # 简单规则: 6开头=sh, 其他=sz (00/30/...)
        prefixed_code = stock_code
        if stock_code.isdigit():
            if stock_code.startswith('6'):
                prefixed_code = f"sh{stock_code}"
            else:
                prefixed_code = f"sz{stock_code}"
                
        url = f"{self.mootdx_api_url}/api/v1/tick/{prefixed_code}"
        params = {"start": start, "offset": offset}
        
        # 如果不是今天，则需要传 date 参数
        today_int = int(datetime.now(CST).strftime('%Y%m%d'))
        if date_int != today_int:
            params["date"] = date_int
            
        try:
            async with self.http_session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                self.logger.warning(f"Non-200 response for {stock_code}: {response.status}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching batch for {stock_code}: {type(e).__name__}: {e}")
            return []

    async def process_task(self, task: Dict[str, Any]):
        """处理任务主体"""
        stock_code = task['code']
        now = datetime.now(CST)
        trade_date_str = now.strftime('%Y-%m-%d')
        date_int = int(now.strftime('%Y%m%d'))
        
        logger.info(f"🔍 Processing task: {stock_code} (Vol diff: {task['current_vol'] - task['last_vol']})")
        
        # 1. 获取现有指纹
        self.logger.debug(f"Getting DB fingerprints for {stock_code}")
        existing_fps = await self.get_latest_ticks_from_db(stock_code, trade_date_str)
        existing_fps_set = set(existing_fps)
        self.logger.debug(f"Got {len(existing_fps)} fingerprints for {stock_code}")
        
        all_new_rows = []
        start_index = 0
        max_backtrace = 5 # 最多追溯 5 个批次 (4000条)
        
        for i in range(max_backtrace):
            self.logger.debug(f"Fetching batch {i} for {stock_code}, start={start_index}")
            batch = await self.fetch_batch(stock_code, date_int, start=start_index)
            if not batch:
                break
            
            self.logger.debug(f"Fetched {len(batch)} ticks for {stock_code}")
            
            new_in_batch = []
            matched = False
            
            for item in batch:
                # 预处理数据: API 返回 ['time', 'price', 'volume', 'type']
                time_str = item.get('time', '09:30')
                if len(time_str) == 5: time_str += ":00"
                price = float(item.get('price', 0))
                volume = int(item.get('volume', 0)) # 已经是股数 (API标准化转换过)
                direction_str = item.get('type', 'NEUTRAL')
                direction = self._map_direction(direction_str)
                
                fp = self._gen_fingerprint(time_str, price, volume, direction)
                
                if fp in existing_fps_set:
                    # 发现重叠点
                    matched = True
                    break
                else:
                    new_in_batch.append((
                        stock_code,
                        now.date(),
                        time_str,
                        price,
                        volume,
                        price * volume,
                        direction
                    ))
            
            if new_in_batch:
                all_new_rows.extend(new_in_batch)
            
            if matched:
                break
            else:
                start_index += len(batch)
                self.logger.debug(f"Gap detected for {stock_code}, backtracing to start={start_index}...")
                await asyncio.sleep(0.05) 

        # 2. 写入数据库
        if all_new_rows:
            # 去重
            unique_rows = list(dict.fromkeys(all_new_rows))
            # 翻转顺序：API返回通常是最新的在前，我们要写入数据库
            # 但实际上 ClickHouse 不在乎顺序，去重逻辑也不在乎
            unique_rows.sort(key=lambda x: x[2]) # 按 tick_time 排序
            
            count = await self._write_to_clickhouse(unique_rows)
            self.logger.info(f"✅ {stock_code}: Incremental sync finished. Added {count} new ticks.")
        else:
            self.logger.debug(f"⏩ {stock_code}: No new unique ticks found.")

    def _map_direction(self, type_val) -> int:
        """
        映射买卖方向: 0=买(BUY) 1=卖(SELL) 2=中性(NEUTRAL)
        支持数字映射(兼容原有逻辑)和字符串映射(API标准化后)
        """
        if isinstance(type_val, str):
            if type_val == 'BUY': return 0
            if type_val == 'SELL': return 1
            return 2
        
        # 兼容旧有数字格式 (如果某些 API 还没标准化)
        if type_val == 0: return 0 # BUY
        if type_val == 1: return 1 # SELL
        return 2 # NEUTRAL

    async def _write_to_clickhouse(self, rows: List[Tuple]) -> int:
        try:
            async with self.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "INSERT INTO tick_data_intraday (stock_code, trade_date, tick_time, price, volume, amount, direction) VALUES",
                        rows
                    )
            return len(rows)
        except Exception as e:
            logger.error(f"ClickHouse write error: {e}")
            return 0

    async def close(self):
        """释放资源"""
        if self.clickhouse_pool:
            self.clickhouse_pool.close()
            await self.clickhouse_pool.wait_closed()
        if self.http_session:
            await self.http_session.close()
        if self.redis:
            await self.redis.close()

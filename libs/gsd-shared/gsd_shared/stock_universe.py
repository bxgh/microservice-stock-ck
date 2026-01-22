
import logging
import asyncio
import json
import yaml
from pathlib import Path
from typing import List, Optional, Union
from datetime import datetime
import aiomysql
import redis.asyncio as redis
from .validators import is_valid_a_stock

logger = logging.getLogger(__name__)

# 默认 A 股数量常量 (含缓冲)
DEFAULT_TOTAL_A_SHARES = 5360

class StockUniverseService:
    """
    统一股票全域服务 (Single Source of Truth)
    
    职责:
    1. 提供全市场 A 股名单 (get_all_a_stocks)
    2. 提供分片股票名单 (get_shard_stocks)
    3. 提供当日实际交易股票 (get_today_traded_stocks)
    4. 统一执行有效性校验与代码标准化 (Exclude BJ/B-share)
    """
    
    def __init__(
        self, 
        redis_client: Optional[redis.Redis] = None,
        mysql_config: Optional[dict] = None,
        clickhouse_client: Optional[object] = None, # ClickHouseClient instance
        local_cache_dir: str = "/app/data/cache"
    ):
        self.redis = redis_client
        self.mysql_config = mysql_config
        self.ch_client = clickhouse_client
        self.cache_dir = Path(local_cache_dir)
        
    async def get_all_a_stocks(self) -> List[str]:
        """
        获取全市场沪深 A 股代码 (排除北交所)
        优先级: Redis -> MySQL -> 硬编码降级
        """
        # 1. Redis Source
        if self.redis:
            try:
                codes = await self.redis.smembers("metadata:stock_codes")
                if codes:
                    valid_codes = self._filter_and_normalize(list(codes))
                    logger.info(f"✅ [StockUniverse] From Redis: {len(valid_codes)} stocks")
                    return valid_codes
            except Exception as e:
                logger.warning(f"⚠️ [StockUniverse] Redis fetch failed: {e}")
        
        # 2. MySQL Source
        if self.mysql_config:
            try:
                # 使用临时连接 (避免持有长连接)
                async with aiomysql.create_pool(**self.mysql_config) as pool:
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            # 优先使用 stock_basic_info (L=上市)
                            await cur.execute("""
                                SELECT symbol FROM alwaysup.stock_basic_info 
                                WHERE list_status = 'L' 
                                AND market IN ('主板', '中小板', '创业板', '科创板')
                            """)
                            rows = await cur.fetchall()
                            if rows:
                                codes = [r[0] for r in rows]
                                valid_codes = self._filter_and_normalize(codes)
                                logger.info(f"✅ [StockUniverse] From MySQL: {len(valid_codes)} stocks")
                                return valid_codes
            except Exception as e:
                logger.warning(f"⚠️ [StockUniverse] MySQL fetch failed: {e}")
                
        # 3. Fallback (TODO: Can fallback to a local file/config if strictly needed)
        logger.error("❌ [StockUniverse] All sources failed to provide stock list")
        return []

    async def get_shard_stocks(self, shard_index: int, total_shards: int = 3) -> List[str]:
        """
        获取指定分片的股票列表
        优先级: Redis Shard Key -> Local File Cache -> Re-calcuated from All
        """
        # 1. Redis Shard Key
        if self.redis:
            key = f"metadata:stock_codes:shard:{shard_index}"
            try:
                codes = await self.redis.smembers(key)
                if codes:
                    valid = self._filter_and_normalize(list(codes))
                    # Async update local cache
                    asyncio.create_task(self._save_local_cache(f"shard_{shard_index}.json", valid))
                    return valid
            except Exception as e:
                logger.warning(f"⚠️ [StockUniverse] Redis shard fetch failed: {e}")

        # 2. Local File Cache
        cached = await self._load_local_cache(f"shard_{shard_index}.json")
        if cached:
            logger.info(f"✅ [StockUniverse] From Local Cache: {len(cached)} stocks (Shard {shard_index})")
            return cached
            
        # 3. Recalculate from All (Last Resort)
        logger.warning(f"⚠️ [StockUniverse] Recalculating shard {shard_index} from FULL list")
        all_stocks = await self.get_all_a_stocks()
        return self._shard_filter(all_stocks, shard_index, total_shards)

    async def get_today_traded_stocks(self, trade_date: str) -> List[str]:
        """
        获取当日实际交易的股票列表 (基于 K 线或 Tick 数据)
        优先级: ClickHouse (KLine) -> MySQL (KLine) -> Get All (Fallback)
        """
        db_date = trade_date.replace("-", "") # YYYYMMDD
        
        # 1. ClickHouse Source
        if self.ch_client:
            try:
                # 排除 BJ 代码
                query = f"""
                    SELECT DISTINCT stock_code FROM stock_data.stock_kline_daily 
                    WHERE trade_date = '{db_date}'
                    AND stock_code NOT LIKE '%4%' 
                    AND stock_code NOT LIKE '%8%' 
                    AND stock_code NOT LIKE '%9%'
                    AND stock_code NOT LIKE 'bj.%'
                """
                # Client might be async or sync depending on impl, wrap carefully
                # Assuming ClickHouseClient exposes a sync/async execute
                if hasattr(self.ch_client, 'execute_async'):
                    rows = await self.ch_client.execute_async(query)
                elif hasattr(self.ch_client, 'client'):
                     # asynch client
                     rows = await self.ch_client.client.execute(query)
                else: 
                     # sync client wrapper (run in executor if needed, but for now assuming fast)
                     rows = self.ch_client.execute(query) # Using wrapper method if available
                     
                if rows:
                    return self._filter_and_normalize([r[0] for r in rows])
            except Exception as e:
                logger.warning(f"⚠️ [StockUniverse] ClickHouse fetch failed: {e}")

        # 2. MySQL Source
        if self.mysql_config:
            try:
                 async with aiomysql.create_pool(**self.mysql_config) as pool:
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            # 格式化 %% 来转义 %
                            sql = """
                                SELECT code FROM stock_kline_daily 
                                WHERE trade_date = %s
                                AND code NOT LIKE '%%4%%'
                                AND code NOT LIKE '%%8%%'
                                AND code NOT LIKE '%%9%%'
                                AND code NOT LIKE 'bj.%%'
                            """
                            await cur.execute(sql, (trade_date,))
                            rows = await cur.fetchall()
                            if rows:
                                return [r[0] for r in rows] # Already normalized in DB usually
            except Exception as e:
                logger.warning(f"⚠️ [StockUniverse] MySQL fetch failed: {e}")

        # 3. Fallback to All
        logger.warning(f"⚠️ [StockUniverse] No K-Line data found for {trade_date}, falling back to ALL")
        return await self.get_all_a_stocks()

    # --- Helper Methods ---

    def normalize_code(self, code: str) -> str:
        """标准化为 6 位纯数字"""
        code = str(code).strip()
        if '.' in code:
            parts = code.split('.')
            return parts[0] if len(parts[0]) == 6 else parts[-1]
        
        # 移除前缀
        lower = code.lower()
        if lower.startswith(('sh', 'sz')):
            return code[2:]
            
        return code

    def is_valid_a_stock(self, code: str) -> bool:
        """Wrapper for shared validator"""
        return is_valid_a_stock(code)
    
    def _filter_and_normalize(self, raw_codes: List[str]) -> List[str]:
        """批量标准化并过滤"""
        valid = set()
        for c in raw_codes:
            norm = self.normalize_code(c)
            if self.is_valid_a_stock(norm):
                valid.add(norm)
        return sorted(list(valid))

    def _shard_filter(self, stocks: List[str], shard_index: int, total: int) -> List[str]:
        import xxhash
        return [
            s for s in stocks 
            if xxhash.xxh64(s).intdigest() % total == shard_index
        ]
        
    async def _save_local_cache(self, filename: str, data: List[str]):
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path = self.cache_dir / filename
            # Write to temp then atomic rename
            tmp_path = path.with_suffix(".tmp")
            loop = asyncio.get_running_loop()
            
            content = json.dumps({"updated_at": datetime.now().isoformat(), "data": data})
            await loop.run_in_executor(None, tmp_path.write_text, content)
            tmp_path.rename(path)
        except Exception as e:
            logger.warning(f"Failed to write local cache {filename}: {e}")

    async def _load_local_cache(self, filename: str) -> List[str]:
        path = self.cache_dir / filename
        if not path.exists():
            return []
        try:
            content = path.read_text()
            return json.loads(content).get("data", [])
        except:
            return []

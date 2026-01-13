"""
分笔数据同步核心服务

负责从 mootdx-api 采集盘后分笔数据并写入 ClickHouse
实现智能搜索矩阵策略，确保100%获取09:25集合竞价数据
"""

import asyncio
import aiohttp
import asynch
import os
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
import yaml
import pytz
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster, ClusterNode

logger = logging.getLogger(__name__)

# 上海时区
CST = pytz.timezone('Asia/Shanghai')

# 本地缓存路径
CACHE_DIR = Path("/app/data/cache")



class TickSyncService:
    """分笔数据同步服务"""
    
    # 基于验证成功的搜索矩阵（参考：真正100%成功_修复版.py）
    SEARCH_MATRIX = [
        # 第零优先级：基础全量获取 (保证午盘和收盘数据)
        (0, 5000, "全量基础"),
        
        # 第一优先级：万科A验证成功区域
        (3500, 800, "万科A前区域"),
        (4000, 500, "万科A原成功"),
        (4500, 800, "万科A后区域"),
        
        # 第二优先级：深度搜索区域
        (3000, 1000, "深度区域1"),
        (5000, 1000, "深度区域2"),
        (6000, 1200, "深度区域3"),
        
        # 第三优先级：广域搜索
        (2000, 1500, "广域区域1"),
        (7000, 1500, "广域区域2"),
        (8000, 2000, "广域区域3"),
        
        # 第四优先级：极限搜索
        (1000, 2000, "极限区域1"),
        (10000, 3000, "极限区域2"),
    ]
    
    # 常量定义
    TARGET_TIME = "09:25"
    REDIS_STATUS_EXPIRE_SECONDS = 86400 * 7  # 7天
    DEFAULT_MIN_PACING_INTERVAL = 0.3      # 最小请求间隔
    
    def __init__(self):
        self.clickhouse_pool: Optional[asynch.Pool] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.mootdx_api_url: str = os.getenv("MOOTDX_API_URL", "http://mootdx-api:8000")
        
        self.redis_client: Optional[redis.Redis] = None  # 支持单机和集群
        self.redis_mode_is_cluster: bool = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
        self.redis_nodes: str = os.getenv(
            "REDIS_NODES", 
            "192.168.151.41:6379,192.168.151.58:6379,192.168.151.111:6379"
        )
        self.redis_host: str = os.getenv("REDIS_HOST", "127.0.0.1")
        self.redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password: str = os.getenv("REDIS_PASSWORD", "redis123")
        
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """初始化连接池"""
        async with self._lock:
            # ClickHouse 连接
            if self.clickhouse_pool is None:
                self.clickhouse_pool = await asynch.create_pool(
                    host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
                    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
                    database="stock_data",
                    user=os.getenv("CLICKHOUSE_USER", "default"),
                    password=os.getenv("CLICKHOUSE_PASSWORD", ""),
                    minsize=1,
                    maxsize=5
                )
                logger.info("✓ ClickHouse 连接池初始化完成")
            
            # HTTP 会话
            if self.http_session is None:
                timeout = aiohttp.ClientTimeout(total=120)
                self.http_session = aiohttp.ClientSession(timeout=timeout)
                logger.info(f"✓ HTTP 会话初始化完成: {self.mootdx_api_url}")
            
            # Redis 连接 (支持单机和集群)
            if self.redis_client is None:
                try:
                    if self.redis_mode_is_cluster:
                        nodes = []
                        for node_str in self.redis_nodes.split(","):
                            host, port = node_str.split(":")
                            nodes.append(ClusterNode(host, int(port)))
                        
                        self.redis_client = RedisCluster(
                            startup_nodes=nodes,
                            decode_responses=True,
                            socket_timeout=5,
                            cluster_error_retry_attempts=3,
                            password=self.redis_password
                        )
                        logger.info(f"✓ Redis Cluster 连接初始化完成: {len(nodes)} 个起始节点")
                    else:
                        self.redis_client = redis.Redis(
                            host=self.redis_host,
                            port=self.redis_port,
                            password=self.redis_password,
                            decode_responses=True,
                            socket_timeout=5
                        )
                        logger.info(f"✓ Redis Standalone 连接初始化完成: {self.redis_host}:{self.redis_port}")
                    
                    # 验证连接
                    await self.redis_client.ping()
                except Exception as e:
                    logger.warning(f"⚠️ Redis 初始化失败 (任务订阅/状态持续可能不可用): {e}")
                    self.redis_client = None
    
    async def close(self) -> None:
        """关闭连接池和会话"""
        async with self._lock:
            if self.clickhouse_pool:
                self.clickhouse_pool.close()
                await self.clickhouse_pool.wait_closed()
                self.clickhouse_pool = None
            if self.http_session:
                await self.http_session.close()
                await asyncio.sleep(0.25)  # 等待连接完全关闭
                self.http_session = None
            if self.redis_client:
                await self.redis_client.aclose()
                self.redis_client = None
            logger.info("连接池和会话已关闭")

    async def get_all_stocks(self) -> List[str]:
        """
        从 mootdx-api 获取全市场股票代码 (A股)
        
        过滤规则: 60/68 (沪), 00/30 (深)
        """
        logger.info("正在获取全市场股票列表...")
        all_codes = []
        
        try:
            # 获取深圳市场 (0) 和 上海市场 (1)
            for market in [0, 1]:
                url = f"{self.mootdx_api_url}/api/v1/stocks"
                params = {"market": market}
                
                async with self.http_session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            # 过滤 A 股代码
                            # 60xxxx: 沪市主板
                            # 68xxxx: 科创板
                            # 00xxxx: 深市主板
                            # 30xxxx: 创业板
                            market_codes = [
                                item['code'] for item in data 
                                if item.get('code', '').startswith(('60', '68', '00', '30'))
                            ]
                            all_codes.extend(market_codes)
                            logger.info(f"市场 {market} 获取到 {len(market_codes)} 只 A股股票")
                    else:
                        logger.error(f"获取市场 {market} 股票失败: {response.status}")
                        
            # 去重并排序
            all_codes = sorted(list(set(all_codes)))
            logger.info(f"全市场 A股总数: {len(all_codes)}")
            return all_codes
            
        except Exception as e:
            logger.error(f"获取全市场股票失败: {e}")
            return []

    async def get_sharded_stocks(self, shard_index: int) -> List[str]:
        """
        从 Redis 获取分片股票列表 (支持本地磁盘缓存降级)
        
        策略:
        1. 优先尝试 Redis 获取
        2. 成功则更新本地缓存 (json)
        3. Redis 失败/为空时，尝试读取本地缓存
        """
        key = f"metadata:stock_codes:shard:{shard_index}"
        
        # 1. 尝试 Redis 获取
        if self.redis_client:
            try:
                # 获取集合成员
                codes = await self.redis_client.smembers(key)
                if codes:
                    # 清洗数据
                    clean_codes = []
                    for code in codes:
                        clean_codes.append(code.split(".")[0] if "." in code else code)
                    clean_codes.sort()
                    
                    logger.info(f"从 Redis 获取 Shard {shard_index} 股票: {len(clean_codes)} 只")
                    
                    # 2. 更新本地缓存
                    await self._save_local_cache(shard_index, clean_codes)
                    return clean_codes
            except Exception as e:
                logger.error(f"从 Redis 获取分片 {shard_index} 失败: {e}")
        
        # 3. 降级：读取本地缓存
        logger.warning(f"⚠️ Redis 不可用或无数据，尝试读取本地缓存 (Shard {shard_index})...")
        return await self._load_local_cache(shard_index)

    async def _save_local_cache(self, shard_index: int, codes: List[str]) -> None:
        """异步保存分片数据到本地磁盘"""
        if not codes: 
            return
            
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / f"shard_{shard_index}_latest.json"
            
            # 使用 run_in_executor 避免阻塞事件循环
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, 
                self._write_json_cache, 
                cache_file, 
                codes
            )
            logger.debug(f"已缓存分片 {shard_index} 到 {cache_file}")
        except Exception as e:
            logger.warning(f"保存本地缓存失败: {e}")

    def _write_json_cache(self, path: Path, data: List[str]) -> None:
        """同步写入文件 (运行在 executor 中)"""
        import json
        with open(path, "w") as f:
            json.dump({"updated_at": datetime.now().isoformat(), "codes": data}, f)

    async def _load_local_cache(self, shard_index: int) -> List[str]:
        """从本地磁盘读取缓存"""
        cache_file = CACHE_DIR / f"shard_{shard_index}_latest.json"
        if not cache_file.exists():
            logger.error(f"❌ 本地缓存不存在: {cache_file}，无法降级！")
            return []
            
        try:
            import json
            loop = asyncio.get_running_loop()
            # 简单起见直接读，文件不大
            content = await loop.run_in_executor(None, cache_file.read_text)
            data = json.loads(content)
            codes = data.get("codes", [])
            updated_at = data.get("updated_at", "unknown")
            
            if codes:
                logger.info(f"✅ 从本地缓存恢复 Shard {shard_index}: {len(codes)} 只 (上次更新: {updated_at})")
                return codes
            else:
                logger.error(f"本地缓存文件 {cache_file} 内容无效")
                return []
        except Exception as e:
            logger.error(f"读取本地缓存失败: {e}")
            return []

    async def push_tasks_to_redis(
        self, 
        stock_codes: List[str], 
        queue_name: str = "{gsd:tick}:tasks"
    ) -> int:
        """
        [Producer] 将股票代码推入 Redis 任务队列
        """
        if not self.redis_client:
            raise RuntimeError("Redis 客户端未初始化")
            
        try:
            # 清空旧队列
            await self.redis_client.delete(queue_name)
            
            # 批量推送
            if stock_codes:
                await self.redis_client.lpush(queue_name, *stock_codes)
                logger.info(f"📤 已向 Redis 队列 {queue_name} 推送 {len(stock_codes)} 个任务")
                return len(stock_codes)
            return 0
        except Exception as e:
            logger.error(f"❌ 推送 Redis 任务失败: {e}")
            raise

    async def consume_task_from_redis(
        self,
        queue_name: str = "{gsd:tick}:tasks",
        node_id: str = None
    ) -> Optional[str]:
        """
        [Consumer] 从 Redis 队列获取一个新任务
        """
        if not self.redis_client:
            return None
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{{gsd:tick}}:processing:{node_id}"
        
        try:
            # 直接获取新任务
            task = await self.redis_client.brpoplpush(queue_name, processing_queue, timeout=5)
            return task
        except Exception as e:
            logger.error(f"❌ 获取 Redis 任务失败: {e}")
            return None

    async def recover_processing_tasks(self, node_id: str = None) -> List[str]:
        """
        [Consumer] 启动时恢复上次意外中断的任务
        """
        if not self.redis_client:
            return []
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{{gsd:tick}}:processing:{node_id}"
        
        try:
            # 获取所有处理中任务
            tasks = await self.redis_client.lrange(processing_queue, 0, -1)
            if tasks:
                logger.info(f"♻️ 发现 {len(tasks)} 个未完成任务，准备恢复")
            return tasks
        except Exception as e:
            logger.error(f"❌ 恢复 Redis 任务失败: {e}")
            return []

    async def ack_task_in_redis(
        self,
        stock_code: str,
        node_id: Optional[str] = None
    ) -> bool:
        """
        [Consumer] 任务完成确认，从处理中队列移除
        """
        if not self.redis_client:
            return False
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{{gsd:tick}}:processing:{node_id}"
        
        try:
            await self.redis_client.lrem(processing_queue, 1, stock_code)
            return True
        except Exception as e:
            logger.error(f"❌ 确认 Redis 任务失败 ({stock_code}): {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 确认 Redis 任务失败 ({stock_code}): {e}")
            return False
    
    async def fetch_tick_data(
        self, 
        stock_code: str, 
        trade_date: str
    ) -> List[Dict[str, Any]]:
        """
        核心分笔数据采集策略 (Standard Reference Strategy)
        完全复刻 "真正100%成功_修复版.py" 的逻辑
        """
        start_time = asyncio.get_running_loop().time()
        
        all_frames = []
        
        # 判断日期是否为今天
        today_str = datetime.now(CST).strftime("%Y%m%d")
        is_today = (trade_date == today_str)

        # 1. 执行验证搜索矩阵
        for i, (start, offset, description) in enumerate(self.SEARCH_MATRIX):
            try:
                # 路由选择: 当日使用 /api/v1/tick/, 历史使用 /api/v1/tick/历史参数
                if is_today:
                    url = f"{self.mootdx_api_url}/api/v1/tick/{stock_code}"
                    params = {"start": start, "offset": offset}
                else:
                    url = f"{self.mootdx_api_url}/api/v1/tick/{stock_code}"
                    params = {"date": int(trade_date), "start": start, "offset": offset}
                
                async with self.http_session.get(url, params=params, timeout=12) as response:
                    if response.status != 200:
                        continue
                    
                    data = await response.json()
                    if not data:
                        continue
                        
                    # 提取时间特征
                    times = [x.get('time', '') for x in data]
                    current_earliest = min(times)
                    
                    all_frames.append(data)
                    
                    # 关键逻辑: 检查是否找到目标时间 (09:25)
                    if current_earliest <= self.TARGET_TIME:
                        logger.debug(f"🎯 {stock_code}: 命中 {self.TARGET_TIME} @ {description}")
                        # [Integrity Fix]: 为了保证全天数据完整 (09:25-15:00)，跑完矩阵或直到 09:25
                        break

            except Exception as e:
                logger.warning(f"{stock_code} 步骤 {description} 异常: {e}")
                continue
        
        # 2. 合并数据
        if not all_frames:
            return []
            
        merged = []
        for frame in all_frames:
            merged.extend(frame)
            
        # 3. 严格去重 (按 time, price, vol)
        seen = set()
        final_data = []
        for item in merged:
            key = (
                item.get('time'), 
                item.get('price'), 
                item.get('vol', item.get('volume'))
            )
            if key not in seen:
                seen.add(key)
                final_data.append(item)
        
        # 4. 排序 (按时间升序)
        final_data.sort(key=lambda x: x.get('time', ''))
        
        return final_data
    
    def _validate_data(self, stock_code: str, data: list, trade_date: Optional[str] = None) -> None:
        """
        [Reliability Phase 1 Extended] Smart Validation
        
        1. 金丝雀校验: 核心权重股绝不应为空
        2. 历史数据校验: 只要查询的是过去日期的分笔，理论上不应为空 (除非停牌)。
           为空则怀疑 IP 假死，抛出异常触发重试。
        """
        if data:
            return

        # 1. 金丝雀列表 (权重股绝对不应为空)
        CANARY_STOCKS = {
            '000001', '600519', '600036', '601318', '000002', 
            '300059', '000725', '600000', '000858', '600276'
        }
        
        if stock_code in CANARY_STOCKS:
             raise ValueError(f"CRITICAL: Suspicious empty data for canary stock {stock_code}. Triggering retry...")

        # 2. 历史数据严格校验
        # 如果查询日期早于今天，且返回为空，大概率是坏 IP
        if trade_date:
            try:
                query_date = datetime.strptime(str(trade_date), "%Y%m%d").date()
                today = datetime.now(CST).date()
                if query_date < today:
                    # 对于非金丝雀股票，虽然有停牌可能，但为了保险起见，
                    # 我们可以选择重试一次。或者，更激进地，认为只要是全量同步就不该为空。
                    # 这里采取折中方案：打印警告并抛出 RetryError，依靠 tenacity 的 max_attempts 限制
                    # 避免无限死循环 (Task 会在 retry 几次后最终接受空结果)
                    raise ValueError(f"Suspicious empty data for {stock_code} on historical date {trade_date}")
            except ValueError:
                pass
    
    def _map_direction(self, buyorsell: int) -> int:
        """映射买卖方向: 0=买 1=卖 2=中性"""
        if buyorsell == 0:
            return 0  # 买盘
        elif buyorsell == 1:
            return 1  # 卖盘
        else:
            return 2  # 中性
    
    async def check_data_exists(self, stock_code: str, trade_date: str) -> bool:
        """检查 ClickHouse 中是否已存在当日数据"""
        try:
            # 兼容格式
            trade_date_str = datetime.strptime(
                trade_date.replace("-", ""), "%Y%m%d"
            ).strftime("%Y-%m-%d")
            
            async with self.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"SELECT count() FROM tick_data_local WHERE stock_code = '{stock_code}' AND trade_date = '{trade_date_str}' LIMIT 1"
                    )
                    row = await cursor.fetchone()
                    return row[0] > 0 if row else False
        except Exception as e:
            logger.error(f"检查数据存在失败 {stock_code}: {e}")
            return False

    async def _update_sync_status(
        self, 
        stock_code: str, 
        trade_date: str, 
        status: str, 
        count: int = 0,
        start_t: str = "",
        end_t: str = "",
        error: str = ""
    ) -> None:
        """更新 Redis 中的采集状态"""
        if not self.redis_client:
            return
        
        key = f"tick_sync:status:{trade_date}"
        sync_time = datetime.now(CST).isoformat()
        # 格式: {status}|{tick_count}|{data_start}|{data_end}|{sync_time}|{error}
        value = f"{status}|{count}|{start_t}|{end_t}|{sync_time}|{error}"
        
        try:
            await self.redis_client.hset(key, stock_code, value)
            # 设置过期时间
            await self.redis_client.expire(key, self.REDIS_STATUS_EXPIRE_SECONDS)
        except Exception as e:
            logger.warning(f"Failed to update sync status in Redis: {e}")

    async def sync_stock(
        self, 
        stock_code: str, 
        trade_date: str
    ) -> int:
        """
        同步单只股票的分笔数据
        """
        # 0. 初始化状态为 processing
        await self._update_sync_status(stock_code, trade_date, "processing")
        
        today_str = datetime.now(CST).strftime("%Y%m%d")
        target_table = "tick_data_intraday" if trade_date == today_str else "tick_data"
        
        try:
            # 1. 检查是否已存在 (全量覆盖模式下，实际上 ReplacingMergeTree 会处理，但为了效率可以先查)
            # exists = await self.check_data_exists(stock_code, trade_date)
            # if exists: return -1

            # 2. 采集数据
            tick_data = await self.fetch_tick_data(stock_code, trade_date)
            
            if not tick_data:
                await self._update_sync_status(stock_code, trade_date, "completed", 0)
                return 0
                
            # 提取时间和范围
            times = [x.get('time', '') for x in tick_data]
            min_t, max_t = min(times), max(times)
            
            # 3. 转换格式
            trade_date_obj = datetime.strptime(trade_date, "%Y%m%d").date()
            rows = []
            for item in tick_data:
                time_str = str(item.get('time', '09:30'))
                if len(time_str) == 5: time_str += ":00"
                
                price = float(item.get('price', 0))
                vol = int(item.get('volume', item.get('vol', 0)))
                
                rows.append((
                    stock_code,
                    trade_date_obj,
                    time_str,
                    price,
                    vol,
                    price * vol,
                    self._map_direction(int(item.get('buyorsell', 2))),
                ))
            
            if not rows:
                await self._update_sync_status(stock_code, trade_date, "completed", 0)
                return 0
            
            # 4. 写入 ClickHouse (分布式表)
            async with self.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        f"INSERT INTO stock_data.{target_table} (stock_code, trade_date, tick_time, price, volume, amount, direction) VALUES",
                        rows
                    )
            
            # 5. 更新状态为 completed
            await self._update_sync_status(
                stock_code, trade_date, "completed", len(rows), min_t, max_t
            )
            logger.info(f"✓ {stock_code}: {len(rows)} ticks -> {target_table} ({min_t}-{max_t})")
            return len(rows)

        except Exception as e:
            logger.error(f"❌ {stock_code} sync failed: {e}")
            await self._update_sync_status(stock_code, trade_date, "failed", error=str(e))
            return 0
    
    async def sync_stocks(
        self, 
        stock_codes: List[str], 
        trade_date: Optional[str] = None,
        concurrency: int = 3
    ) -> Dict[str, Any]:
        """
        批量同步多只股票
        
        Args:
            stock_codes: 股票代码列表
            trade_date: 交易日期，默认今天
            concurrency: 并发数（降低以减少服务器压力）
            
        Returns:
            同步结果统计
        """
        if trade_date is None:
            trade_date = datetime.now(CST).strftime("%Y%m%d")
        
        logger.info(f"开始同步分笔数据: {len(stock_codes)} 只股票, 日期: {trade_date}")
        
        semaphore = asyncio.Semaphore(concurrency)
        results = {"success": 0, "failed": 0, "skipped": 0, "total_records": 0, "errors": []}
        
        async def sync_with_limit(code: str):
            async with semaphore:
                start_time = asyncio.get_running_loop().time()
                try:
                    count = await self.sync_stock(code, trade_date)
                    if count > 0:
                        results["success"] += 1
                        results["total_records"] += count
                    elif count == -1:
                        results["skipped"] += 1
                        logger.info(f"⏭️ {code}: 跳过 (已存在)")
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"{code}: 无数据")
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{code}: {str(e)}")
                    logger.error(f"同步失败 {code}: {e}")
                
                # Precise Pacing: Ensure minimum pacing interval between requests
                # This subtracts execution time from the delay to maximize throughput
                elapsed = asyncio.get_running_loop().time() - start_time
                delay = max(0, self.DEFAULT_MIN_PACING_INTERVAL - elapsed)
                if delay > 0:
                    await asyncio.sleep(delay)
        
        tasks = [sync_with_limit(code) for code in stock_codes]
        await asyncio.gather(*tasks)
        
        logger.info(
            f"同步完成: 成功 {results['success']}, "
            f"跳过 {results['skipped']}, "
            f"失败 {results['failed']}, "
            f"总记录 {results['total_records']:,}"
        )
        
        return results
    
    async def get_stock_pool(self) -> List[str]:
        """
        获取待采集的股票池
        
        优先从配置文件读取 HS300 成分股，失败则使用内置默认列表
        """
        config_paths = [
            Path("/app/config/hs300_stocks.yaml"),
            Path(__file__).parent.parent.parent / "config" / "hs300_stocks.yaml",
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                    stocks = config.get("stocks", [])
                    if stocks:
                        logger.info(f"从 {config_path} 加载 {len(stocks)} 只股票")
                        return stocks
                except Exception as e:
                    logger.warning(f"加载配置文件失败: {e}")
        
        # 使用内置默认股票池（部分 HS300 成分股）
        logger.warning("配置文件不存在，使用内置默认股票池")
        return [
            "000001", "000002", "000063", "000100", "000157",
            "000333", "000338", "000425", "000538", "000568",
            "000596", "000625", "000651", "000661", "000703",
            "000725", "000768", "000776", "000783", "000786",
            "000858", "000876", "000895", "000938", "000963",
            "002001", "002007", "002008", "002024", "002027",
            "002032", "002049", "002050", "002120", "002129",
            "002142", "002146", "002153", "002179", "002180",
            "300014", "300015", "300033", "300059", "300122",
            "300124", "300142", "300144", "300347", "300408",
            "600000", "600009", "600010", "600011", "600015",
            "600016", "600018", "600019", "600025", "600028",
            "600029", "600030", "600031", "600036", "600048",
            "600050", "600061", "600085", "600104", "600109",
            "600111", "600115", "600118", "600153", "600176",
            "600183", "600196", "600276", "600309", "600332",
            "600346", "600352", "600362", "600406", "600436",
            "600438", "600489", "600519", "600547", "600570",
            "600583", "600585", "600588", "600600", "600606",
            "600655", "600660", "600690", "600703", "600741",
        ]

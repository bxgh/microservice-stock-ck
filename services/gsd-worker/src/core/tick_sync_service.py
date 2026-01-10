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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
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
    
    # 目标时间：集合竞价
    TARGET_TIME = "09:25"
    
    def __init__(self):
        self.clickhouse_pool = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.mootdx_api_url = os.getenv("MOOTDX_API_URL", "http://mootdx-api:8000")
        self.redis_cluster: Optional[RedisCluster] = None
        self.redis_nodes = os.getenv(
            "REDIS_NODES", 
            "192.168.151.41:6379,192.168.151.58:6379,192.168.151.111:6379"
        )
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
            
            # Redis Cluster 连接
            if self.redis_cluster is None:
                try:
                    nodes = []
                    for node_str in self.redis_nodes.split(","):
                        host, port = node_str.split(":")
                        nodes.append(ClusterNode(host, int(port)))
                    
                    self.redis_cluster = RedisCluster(
                        startup_nodes=nodes,
                        decode_responses=True,
                        socket_timeout=5,
                        cluster_error_retry_attempts=3
                    )
                    # 验证连接
                    await self.redis_cluster.ping()
                    logger.info(f"✓ Redis Cluster 连接初始化完成: {len(nodes)} 个起始节点")
                except Exception as e:
                    logger.warning(f"⚠️ Redis Cluster 初始化失败 (任务订阅可能不可用): {e}")
                    self.redis_cluster = None
    
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
            if self.redis_cluster:
                await self.redis_cluster.aclose()
                self.redis_cluster = None
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
        if self.redis_cluster:
            try:
                codes = await self.redis_cluster.smembers(key)
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

    async def _save_local_cache(self, shard_index: int, codes: List[str]):
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

    def _write_json_cache(self, path: Path, data: List[str]):
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
        if not self.redis_cluster:
            raise RuntimeError("Redis Cluster 未初始化")
            
        try:
            # 清空旧队列
            await self.redis_cluster.delete(queue_name)
            
            # 批量推送
            if stock_codes:
                await self.redis_cluster.lpush(queue_name, *stock_codes)
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
        if not self.redis_cluster:
            return None
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{{gsd:tick}}:processing:{node_id}"
        
        try:
            # 直接获取新任务
            task = await self.redis_cluster.brpoplpush(queue_name, processing_queue, timeout=5)
            return task
        except Exception as e:
            logger.error(f"❌ 获取 Redis 任务失败: {e}")
            return None

    async def recover_processing_tasks(self, node_id: str = None) -> List[str]:
        """
        [Consumer] 启动时恢复上次意外中断的任务
        """
        if not self.redis_cluster:
            return []
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{{gsd:tick}}:processing:{node_id}"
        
        try:
            # 获取所有处理中任务
            tasks = await self.redis_cluster.lrange(processing_queue, 0, -1)
            if tasks:
                logger.info(f"♻️ 发现 {len(tasks)} 个未完成任务，准备恢复")
            return tasks
        except Exception as e:
            logger.error(f"❌ 恢复 Redis 任务失败: {e}")
            return []

    async def ack_task_in_redis(
        self,
        stock_code: str,
        node_id: str = None
    ) -> bool:
        """
        [Consumer] 任务完成确认，从处理中队列移除
        """
        if not self.redis_cluster:
            return False
            
        if node_id is None:
            node_id = os.getenv("HOSTNAME", "default-node")
            
        processing_queue = f"{{gsd:tick}}:processing:{node_id}"
        
        try:
            await self.redis_cluster.lrem(processing_queue, 1, stock_code)
            return True
        except Exception as e:
            logger.error(f"❌ 确认 Redis 任务失败 ({stock_code}): {e}")
            return False
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
    
    async def fetch_tick_data_sequential(
        self,
        stock_code: str,
        trade_date: str,
        target_time: str = "09:25",
        batch_size: int = 1000  # 从 2000 降回 1000 保持稳定
    ) -> List[Dict[str, Any]]:
        """
        使用顺序批次回溯策略获取分笔数据，增加重试机制和稳定性
        """
        logger.debug(f"开始顺序批次回溯: {stock_code} ({trade_date})")
        
        all_data = []
        start = 0
        found_target = False
        max_batches = 30  # 1000 * 30 = 30000, 足够全天数据
        
        for batch_idx in range(max_batches):
            retry_count = 0
            max_retries = 3
            batch_success = False
            
            end_of_data = False
            
            while retry_count < max_retries:
                try:
                    url = f"{self.mootdx_api_url}/api/v1/tick/{stock_code}"
                    params = {"date": int(trade_date), "start": start, "offset": batch_size}
                    
                    async with self.http_session.get(url, params=params, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            if not data:
                                batch_success = True
                                end_of_data = True
                                break
                                
                            all_data.extend(data)
                            times = [item.get('time', '23:59') for item in data]
                            earliest = min(times)
                            
                            if earliest <= target_time:
                                found_target = True
                            
                            start += len(data)
                            batch_success = True
                            break
                        else:
                            logger.warning(f"SBF {stock_code} 批次 {batch_idx} 失败 ({response.status})，重试 {retry_count+1}")
                except Exception as e:
                    logger.warning(f"SBF {stock_code} 批次 {batch_idx} 异常 ({e})，重试 {retry_count+1}")
                
                retry_count += 1
                await asyncio.sleep(0.2 * retry_count)
            
            if not batch_success:
                logger.error(f"SBF {stock_code} 批次 {batch_idx} 最终失败，跳过")
                break
                
            if end_of_data:
                break

            if found_target:
                logger.info(f"🎯 {stock_code}: 已找齐全天数据 (共 {len(all_data)} 条)")
                break
                
            # 移除无意义的 sleep(0.1)
            
        return all_data
    async def fetch_tick_data_smart(
        self, 
        stock_code: str, 
        trade_date: str
    ) -> List[Dict[str, Any]]:
        """
        使用智能搜索矩阵策略获取分笔数据
        
        策略：
        1. 遍历搜索矩阵（多个 start/offset 组合）
        2. 检查每批数据是否包含目标时间（09:25）
        3. 找到目标后继续1-2步确保完整性
        4. 合并去重并按时间升序排列
        
        Args:
            stock_code: 股票代码（如 000001）
            trade_date: 交易日期（YYYYMMDD）
            
        Returns:
            分笔数据列表
        """
        all_data = []
        found_target = False
        successful_step = None
        
        logger.debug(f"开始智能搜索: {stock_code} ({trade_date})")
        
        for i, (start, offset, description) in enumerate(self.SEARCH_MATRIX):
            try:
                url = f"{self.mootdx_api_url}/api/v1/tick/{stock_code}"
                params = {"date": int(trade_date), "start": start, "offset": offset}
                
                logger.info(f"DEBUG: Requesting {url} with params {params}") # DEBUG
                async with self.http_session.get(url, params=params, timeout=10) as response: # Added timeout
                    logger.info(f"DEBUG: Response status {response.status}") # DEBUG
                    if response.status != 200:
                        logger.warning(f"API 返回 {response.status}: {stock_code} @ {description}")
                        continue
                    
                    data = await response.json()
                    logger.info(f"DEBUG: Got data length {len(data) if data else 0}") # DEBUG
                    
                    if not data:
                        logger.debug(f"搜索步骤 {i+1}/{len(self.SEARCH_MATRIX)} ({description}): 无数据")
                        continue
                    
                    # 获取此批次的时间范围
                    batch_times = [item.get('time', '') for item in data]
                    if not batch_times:
                        continue
                    
                    current_earliest = min(batch_times)
                    current_latest = max(batch_times)
                    
                    logger.debug(
                        f"搜索步骤 {i+1}/{len(self.SEARCH_MATRIX)} ({description}): "
                        f"{len(data)} 条 ({current_earliest} ~ {current_latest})"
                    )
                    
                    # 检查是否找到目标时间
                    if current_earliest <= self.TARGET_TIME:
                        found_target = True
                        successful_step = description
                        logger.info(f"🎯 {stock_code}: 找到 {self.TARGET_TIME} 数据！步骤: {description}")
                        
                        all_data.append(data)
                        
                        # 智能停止：找到目标后继续1-2步确保完整性
                        if found_target and len(all_data) >= 3:
                            logger.debug(f"{stock_code}: 已确保完整性，停止搜索")
                            break
                    else:
                        all_data.append(data)
                
                # 避免服务器压力
                await asyncio.sleep(0.05)
                
            except aiohttp.ClientError as e:
                logger.warning(f"搜索步骤 {description} 失败: {stock_code}, 错误: {e}")
                continue
            except asyncio.TimeoutError:
                logger.warning(f"搜索步骤 {description} 超时: {stock_code}")
                continue
        
        if not all_data:
            logger.debug(f"{stock_code}: 搜索未获取到任何数据")
            return []
        
        # 合并所有批次数据
        merged_data = []
        for batch in all_data:
            merged_data.extend(batch)
        
        # 去重（基于 time + price + volume）
        seen = set()
        unique_data = []
        for item in merged_data:
            key = (item.get('time'), item.get('price'), item.get('volume'))
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        
        # 按时间升序排列
        unique_data.sort(key=lambda x: x.get('time', ''))
        
        if unique_data:
            earliest = unique_data[0].get('time', '')
            latest = unique_data[-1].get('time', '')
            logger.info(
                f"✓ {stock_code}: {len(unique_data)} 条记录 "
                f"({earliest} ~ {latest}) "
                f"{'✅' if earliest <= self.TARGET_TIME else '⚠️'}"
            )
        
        return unique_data
    
    def _map_direction(self, buyorsell: int) -> int:
        """映射买卖方向: 0=买 1=卖 2=中性"""
        if buyorsell == 0:
            return 0  # 买盘
        elif buyorsell == 1:
            return 1  # 卖盘
        else:
            return 2  # 中性
    
    async def sync_stock(
        self, 
        stock_code: str, 
        trade_date: str
    ) -> int:
        """
        同步单只股票的分笔数据
        
        Returns:
            写入记录数
        """
        # 使用顺序批次回溯策略获取数据（确保100%覆盖09:25）
        tick_data = await self.fetch_tick_data_sequential(stock_code, trade_date)
        
        if not tick_data:
            logger.debug(f"{stock_code} 无分笔数据")
            return 0
        
        # 转换日期格式
        trade_date_obj = datetime.strptime(trade_date, "%Y%m%d").date()
        
        # 准备插入数据 - 适配现有表结构
        # 表结构: symbol, trade_date, timestamp, price, volume, amount, direction, data_source, is_auction
        rows = []
        for item in tick_data:
            try:
                # 解析时间字符串为 datetime
                time_str = str(item.get('time', '09:30'))
                if len(time_str) == 5:  # HH:MM 格式
                    time_str = f"{time_str}:00"
                timestamp = datetime.strptime(
                    f"{trade_date} {time_str}", 
                    "%Y%m%d %H:%M:%S"
                )
                
                # 判断是否为集合竞价
                is_auction = 1 if time_str.startswith('09:25') else 0
                
                row = (
                    stock_code,                                    # stock_code
                    trade_date_obj,                                # trade_date
                    time_str,                                      # tick_time
                    float(item.get('price', 0)),                   # price
                    int(item.get('volume', 0)),                    # volume
                    float(item.get('price', 0)) * int(item.get('volume', 0)),  # amount (Decimal)
                    self._map_direction(int(item.get('buyorsell', 2))),  # direction
                )
                rows.append(row)
            except (ValueError, TypeError) as e:
                logger.warning(f"数据转换失败: {item}, 错误: {e}")
                continue
        
        if not rows:
            return 0
        
        # 写入 ClickHouse
        try:
            async with self.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        INSERT INTO tick_data 
                        (stock_code, trade_date, tick_time, price, volume, amount, direction)
                        VALUES
                        """,
                        rows
                    )
            
            logger.info(f"✓ {stock_code}: {len(rows)} 条分笔写入成功")
            return len(rows)
        except Exception as e:
            logger.error(f"❌ {stock_code}: ClickHouse 写入失败: {e}")
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
        results = {"success": 0, "failed": 0, "total_records": 0, "errors": []}
        
        async def sync_with_limit(code: str):
            async with semaphore:
                start_time = asyncio.get_running_loop().time()
                try:
                    count = await self.sync_stock(code, trade_date)
                    if count > 0:
                        results["success"] += 1
                        results["total_records"] += count
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"{code}: 无数据")
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{code}: {str(e)}")
                    logger.error(f"同步失败 {code}: {e}")
                
                # Precise Pacing: Ensure minimum 0.3s interval between requests
                # This subtracts execution time from the delay to maximize throughput
                elapsed = asyncio.get_running_loop().time() - start_time
                delay = max(0, 0.3 - elapsed)
                if delay > 0:
                    await asyncio.sleep(delay)
        
        tasks = [sync_with_limit(code) for code in stock_codes]
        await asyncio.gather(*tasks)
        
        logger.info(
            f"同步完成: 成功 {results['success']}, "
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

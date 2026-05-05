"""
每日股票代码采集任务 (Daily Stock Collection)

功能:
1. 从腾讯云 API (http://124.221.80.250:8000) 拉取全量股票代码
2. 格式化为标准格式 (e.g., 000001.SZ)
3. 缓存到本地 Redis，供 gsd-worker 分片使用
4. 支持手动触发和定时执行

执行时间:
- 每天上午 9:00 (开盘前更新元数据)

Usage:
  python -m jobs.daily_stock_collection
"""

import sys
import asyncio
import logging
import aiohttp
import json
import os
import xxhash
from datetime import datetime
from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster
from gsd_shared.validators import is_valid_a_stock, is_valid_etf, is_valid_index
from gsd_shared.config_loader import get_config
import pytz

# 时区设置 (标准化要求：Asia/Shanghai)
TZ_SHANGHAI = pytz.timezone('Asia/Shanghai')

# 从配置加载核心指数
config = get_config()
CORE_INDICES = [f"{c}.BJ" if c.startswith('8') else (f"{c}.SH" if c.startswith('0') or c.startswith('6') else f"{c}.SZ") for c in config.get("indices", [])]

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DailyStockCollection")

# 腾讯云 API 配置
DEFAULT_CLOUD_API = "http://124.221.80.250:8000/api/v1/stocks/all"
CLOUD_API_URL = os.getenv("CLOUD_API_URL", DEFAULT_CLOUD_API)
HTTP_PROXY = os.getenv("HTTP_PROXY", "http://192.168.151.18:3128")
REDIS_KEY_CODES = "metadata:stock_codes"
REDIS_KEY_INFO = "metadata:stock_info"
REDIS_KEY_SHARD_PREFIX = "metadata:stock_codes:shard"
TOTAL_SHARDS = 3
REDIS_TTL = 3600 * 24 * 14  # 14天，覆盖长假


async def fetch_stock_data():
    """从云端 API 获取全量股票数据"""
    logger.info(f"🚀 开始从云端拉取股票列表: {CLOUD_API_URL}")
    logger.info(f"   使用代理: {HTTP_PROXY}")
    
    # 构建查询参数：仅获取在市的 A 股股票
    params = {
        "security_type": "stock",  # 仅股票类型（排除指数、ETF、基金等）
        "is_listed": "true",       # 仅在市股票（排除退市股票）
        "is_active": "true"        # 仅活跃数据（数据维护状态良好）
    }
    logger.info(f"   过滤条件: {params}")
    
    # 配置代理
    connector = aiohttp.TCPConnector()
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get(CLOUD_API_URL, params=params, proxy=HTTP_PROXY, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"❌ API 请求失败: HTTP {response.status}")
                    return None
                
                data = await response.json()
                items = data.get("items", [])
                total = data.get("total", 0)
                
                logger.info(f"✓ 获取成功: {len(items)} 条记录 (API Total: {total})")
                logger.info(f"   已通过 API 参数过滤退市股票和非股票类型")
                return items
        except Exception as e:
            logger.error(f"❌ 网络请求异常: {e}")
            return None

async def update_redis_cache(redis, items):
    """
    更新 Redis 缓存 (Cluster 兼容策略)
    
    策略:
    1. 检查旧数据是否存在
    2. 直接覆盖写入新数据 (Set 天然支持覆盖)
    3. 失败时至少保留旧数据 (通过 TTL 延长)
    """
    if not items:
        logger.warning("⚠️  无数据可更新，保留现有缓存")
        return False
    
    try:
        # 1. 检查现有数据
        old_count = await redis.scard(REDIS_KEY_CODES)
        if old_count > 0:
            logger.info(f"📦 检测到现有缓存: {old_count} 只股票")
        
        # 2. 准备数据
        stock_codes = []
        stock_info_map = {}
        

        for item in items:
            code = item.get("standard_code")
            exchange = item.get("exchange")
            s_type = item.get("security_type", "stock")
            
            if not code or not exchange:
                continue
            
            formatted_code = f"{code}.{exchange}"
            
            # --- 筛选逻辑 (Epic-002 优化版) ---
            keep = False
            # 1. A 股 (含北证): 全量保留
            if s_type == "stock" and is_valid_a_stock(formatted_code):
                keep = True
            # 2. 指数: 仅保留核心标杆 (由 universe.yaml 指数白名单控制)
            elif is_valid_index(formatted_code):
                keep = True
            
            if keep:
                stock_codes.append(formatted_code)
                stock_info_map[formatted_code] = json.dumps({
                    "name": item.get("name"),
                    "type": s_type
                }, ensure_ascii=False)
        
        # 补充核心指数 (兜底防止 API 未返回)
        for code in CORE_INDICES:
            if code not in stock_codes:
                stock_codes.append(code)
                if code not in stock_info_map:
                    stock_info_map[code] = json.dumps({"name": "基准指数", "type": "index"}, ensure_ascii=False)

        if not stock_codes or len(stock_codes) < 20:
            logger.error(f"❌ 数据解析后数量不足 (Count={len(stock_codes)} < 20)，可能有异常，中止更新")
            # 如果有旧数据，延长 TTL 避免过期
            if old_count > 0:
                await redis.expire(REDIS_KEY_CODES, REDIS_TTL)
                await redis.expire(REDIS_KEY_INFO, REDIS_TTL)
                logger.warning("⚠️  已延长旧数据 TTL")
            return False
        
        # 3. 按分片分组 (使用 xxHash64，与 ClickHouse 一致)
        shard_buckets = [[] for _ in range(TOTAL_SHARDS)]
        for code in stock_codes:
            # xxHash64 计算分片 (与 ClickHouse Distributed 表一致)
            shard_id = xxhash.xxh64(code.encode()).intdigest() % TOTAL_SHARDS
            shard_buckets[shard_id].append(code)
        
        shard_counts = [len(bucket) for bucket in shard_buckets]
        logger.info(f"📊 分片分配: Shard0={shard_counts[0]}, Shard1={shard_counts[1]}, Shard2={shard_counts[2]}")
            
        # 4. 原子性覆盖写入
        logger.info(f"📝 开始更新缓存: {len(stock_codes)} 只股票")
        pipeline = redis.pipeline()
        
        # 删除旧数据 (全量 + 分片)
        pipeline.delete(REDIS_KEY_CODES)
        pipeline.delete(REDIS_KEY_INFO)
        for shard_id in range(TOTAL_SHARDS):
            pipeline.delete(f"{REDIS_KEY_SHARD_PREFIX}:{shard_id}")
        
        # 批量写入全量 Key
        batch_size = 1000
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i+batch_size]
            pipeline.sadd(REDIS_KEY_CODES, *batch)
        
        # 写入分片 Key
        for shard_id, codes in enumerate(shard_buckets):
            shard_key = f"{REDIS_KEY_SHARD_PREFIX}:{shard_id}"
            if codes:
                for i in range(0, len(codes), batch_size):
                    batch = codes[i:i+batch_size]
                    pipeline.sadd(shard_key, *batch)
            pipeline.expire(shard_key, REDIS_TTL)
            
        if stock_info_map:
            pipeline.hset(REDIS_KEY_INFO, mapping=stock_info_map)
        
        # 设置过期时间
        pipeline.expire(REDIS_KEY_CODES, REDIS_TTL)
        pipeline.expire(REDIS_KEY_INFO, REDIS_TTL)
        
        await pipeline.execute()
        
        logger.info(f"✅ Redis 缓存更新完成: {len(stock_codes)} 只股票 (TTL: {REDIS_TTL/3600:.1f}h)")
        logger.info(f"   分片 Key: {REDIS_KEY_SHARD_PREFIX}:0/1/2")
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis 写入失败: {e}")
        # 尝试恢复 TTL (如果旧数据还在)
        try:
            current_count = await redis.scard(REDIS_KEY_CODES)
            if current_count > 0:
                await redis.expire(REDIS_KEY_CODES, REDIS_TTL)
                await redis.expire(REDIS_KEY_INFO, REDIS_TTL)
                logger.warning(f"⚠️  写入失败，但旧数据仍可用 ({current_count} 只)")
        except:
            pass
        return False

async def main():
    """主任务流程"""
    start_time = datetime.now(TZ_SHANGHAI)
    
    redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD", "redis123")
    is_cluster = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
    
    logger.info(f"正在建立 Redis 连接: host={redis_host}, port={redis_port}, cluster={is_cluster}")
    
    try:
        url = f"redis://{redis_host}:{redis_port}"
        if is_cluster:
            redis = await RedisCluster.from_url(
                url,
                password=redis_password,
                decode_responses=True
            )
            logger.info("✓ Redis Cluster 连接初始化完成")
        else:
            redis = Redis.from_url(
                url,
                password=redis_password,
                decode_responses=True
            )
            logger.info("✓ Redis Standalone 连接初始化完成")
        
        # 显式测试连接
        await redis.ping()
        logger.info("✓ Redis 测试连接 (PING) 成功")
    except Exception as e:
        mode_str = "Cluster" if is_cluster else "Standalone"
        logger.error(f"❌ Redis {mode_str} 连接失败: {e}")
        return 1
        
    try:
        # 2. 拉取数据
        items = await fetch_stock_data()
        if not items:
            return 1
            
        # 3. 更新缓存
        success = await update_redis_cache(redis, items)
        
        duration = (datetime.now(TZ_SHANGHAI) - start_time).total_seconds()
        if success:
            logger.info(f"✨ 任务成功完成，耗时: {duration:.2f}s")
            return 0
        else:
            return 1
            
    finally:
        await redis.aclose()
        logger.info("Redis 连接已关闭")

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

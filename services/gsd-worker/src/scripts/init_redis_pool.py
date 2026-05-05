
import os
import redis
import xxhash
import asyncio
from typing import List
from pytdx.hq import TdxHq_API
from loguru import logger
from gsd_shared.validators import is_valid_a_stock

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
SHARD_TOTAL = int(os.getenv("SHARD_TOTAL", 3))

# TDX 配置 (备用列表 - 2026.01.12 Verified)
TDX_HOSTS = [
    {"ip": "175.6.5.153", "port": 7709},  # 湖南电信
    {"ip": "139.9.133.247", "port": 7709}, # 华为云
    {"ip": "119.29.19.242", "port": 7709}, # 腾讯云
    {"ip": "139.159.239.163", "port": 7709}, # 华为云
    {"ip": "119.147.212.81", "port": 7709}, # 广东电信 (备用)
    {"ip": "47.107.64.168", "port": 7709}, # 阿里云
]

def get_stock_list_from_tdx() -> List[str]:
    """从 TDX 获取所有股票代码"""
    api = TdxHq_API()
    connected = False
    
    for host in TDX_HOSTS:
        try:
            logger.info(f"Connecting to TDX {host['ip']}:{host['port']}...")
            with api.connect(host['ip'], host['port']):
                if api.get_security_count(0) > 0: # Check connection
                    connected = True
                    logger.info("Connected!")
                    
                    data = []
                    # 0: 深圳, 1: 上海
                    for market in [0, 1]:
                        count = api.get_security_count(market)
                        for i in range(0, count, 1000):
                            batch = api.get_security_list(market, i)
                            if batch:
                                for item in batch:
                                    code = item['code']
                                    # 简单预过滤，后续会用 is_valid_a_stock 严查
                                    data.append(code)
                    return data
        except Exception as e:
            logger.warning(f"Failed to connect to {host['ip']}: {e}")
            continue
            
    if not connected:
        raise Exception("Unable to connect to any TDX server")
    return []

def main():
    logger.info("🚀 Starting Stock Pool Initialization (v2)...")
    
    # 1. 连接 Redis
    r = redis.Redis(
        host=REDIS_HOST, 
        port=REDIS_PORT, 
        password=REDIS_PASSWORD, 
        decode_responses=True
    )
    try:
        r.ping()
        logger.info(f"✓ Redis connected: {REDIS_HOST}")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return

    # 2. 获取股票列表
    try:
        all_codes = get_stock_list_from_tdx()
        logger.info(f"✓ Fetched {len(all_codes)} raw codes from TDX")
    except Exception as e:
        logger.error(f"❌ Failed to fetch stock list: {e}")
        return

    # 3. 过滤和分片
    valid_codes = []
    shards = {i: [] for i in range(SHARD_TOTAL)}
    北交所_counts = 0
    other_invalid_counts = 0
    
    for code in all_codes:
        # 使用 gsd-shared 的标准校验逻辑 (已包含北交所过滤)
        if not is_valid_a_stock(code):
            if code.startswith(('4', '8', '9')):
                北交所_counts += 1
            else:
                other_invalid_counts += 1
            continue
            
        valid_codes.append(code)
        
        # 计算分片
        shard_id = xxhash.xxh64(code).intdigest() % SHARD_TOTAL
        shards[shard_id].append(code)

    logger.info(f"✓ Filtering Report:")
    logger.info(f"  - Total Raw: {len(all_codes)}")
    logger.info(f"  - Valid A-Share: {len(valid_codes)}")
    logger.info(f"  - Removed BSE (North): {北交所_counts}")
    logger.info(f"  - Removed Other Invalid: {other_invalid_counts}")

    # 4. 写入 Redis
    pipeline = r.pipeline()
    
    # 清理旧数据
    for i in range(SHARD_TOTAL):
        key = f"metadata:stock_codes:shard:{i}"
        pipeline.delete(key)
        
    pipeline.execute()
    
    # 写入新数据
    for i in range(SHARD_TOTAL):
        key = f"metadata:stock_codes:shard:{i}"
        if shards[i]:
            pipeline.sadd(key, *shards[i])
        logger.info(f"  > Shard {i}: {len(shards[i])} stocks -> {key}")
        
    pipeline.execute()
    logger.info("✅ Stock Pool Initialization Complete!")

if __name__ == "__main__":
    main()

"""
TDX 动态 IP 扫描器 (Scanner)

负责从指定网段(Priority CIDRs)中挖掘高质量的 TDX 行情服务器 IP。
设计原则：
1. 定向侦察: 优先扫描华为云、海通等优质网段。
2. 隐蔽行动: 使用随机延迟(Jitter)和低并发防止触发风控。
3. 严格考核: 仅录用延迟低且数据完整的节点。
"""

import asyncio
import logging
import os
import random
import socket
import struct
import time
from typing import List, Tuple, Optional
import redis.asyncio as redis
from mootdx.quotes import Quotes

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("tdx-scanner")

# 优先级网段 (CIDR)
# 华为云段: 124.71.x.x (示例: 124.71.180.0/24)
# 深圳电信/海通: 119.147.x.x
PRIORITY_NETWORKS = [
    ("124.71.187", 7709),   # 华为云节点常见段
    ("119.147.212", 7709),  # 深圳电信核心段
    ("59.36.5", 7709),      # 东莞电信
    ("139.9.51", 7709)      # 华为云备用
]

REDIS_KEY_VERIFIED = "tdx:verified_ips"
SCAN_CONCURRENCY = 20

class IPScanner:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.redis = None

    async def initialize(self):
        address = f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/1"
        self.redis = redis.from_url(address, decode_responses=True)
        logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")

    async def close(self):
        if self.redis:
            await self.redis.close()

    def generate_ips(self, base_ip: str) -> List[str]:
        """生成 C 段 IP 列表 (x.x.x.1 ~ x.x.x.254)"""
        ips = []
        base_parts = base_ip.split('.')[:3]
        prefix = ".".join(base_parts)
        for i in range(1, 255):
            ips.append(f"{prefix}.{i}")
        random.shuffle(ips) # 打乱顺序，避免顺序扫描特征过多
        return ips

    async def verify_ip(self, ip: str, port: int) -> Optional[Tuple[str, int, float]]:
        """
        验证 IP 有效性
        返回: (ip, port, latency) 或 None
        """
        # 1. Jitter (随机延迟)
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # 2. TCP Connect Test
        try:
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=2.0)
            writer.close()
            await writer.wait_closed()
        except Exception:
            return None

        # 3. TDX Protocol & Data Test
        # 尝试连接并获取数据
        start_time = time.time()
        try:
            loop = asyncio.get_event_loop()
            # 同样使用金丝雀(平安银行)测试数据完整性
            client = await loop.run_in_executor(
                None, 
                lambda: Quotes.factory(market='std', bestip=False, server=(ip, port))
            )
            
            # 获取最近 1 根 K 线
            data = await loop.run_in_executor(
                None,
                lambda: client.bars(category=9, market=0, code='000001', start=0, count=1)
            )
            
            latency = (time.time() - start_time) * 1000 # ms
            
            if data is not None and len(data) > 0 and latency < 200:
                logger.info(f"✨ 发现优质节点: {ip}:{port} (延迟: {latency:.1f}ms)")
                return (ip, port, latency)
            else:
                # logger.debug(f"节点 {ip} 数据无效或延迟高 ({latency:.1f}ms)")
                return None
                
        except Exception as e:
            # logger.debug(f"节点 {ip} 协议验证失败: {e}")
            return None

    async def scan_network(self, base_ip: str, port: int):
        logger.info(f"开始扫描网段: {base_ip}.0/24 ...")
        ips = self.generate_ips(base_ip)
        
        sem = asyncio.Semaphore(SCAN_CONCURRENCY)
        valid_ips = []
        
        async def _worker(target_ip):
            async with sem:
                result = await self.verify_ip(target_ip, port)
                if result:
                    valid_ips.append(result)

        tasks = [_worker(ip) for ip in ips]
        await asyncio.gather(*tasks)
        
        logger.info(f"网段 {base_ip} 扫描完成，发现 {len(valid_ips)} 个有效节点")
        return valid_ips

    async def run(self):
        await self.initialize()
        
        all_valid = []
        for base, port in PRIORITY_NETWORKS:
            valid = await self.scan_network(base, port)
            all_valid.extend(valid)
        
        # 保存结果到 Redis
        if all_valid:
            pipeline = self.redis.pipeline()
            pipeline.delete(REDIS_KEY_VERIFIED) # 覆盖更新，保持最新
            for ip, port, lat in all_valid:
                pipeline.sadd(REDIS_KEY_VERIFIED, f"{ip}:{port}")
            await pipeline.execute()
            logger.info(f"已更新 Redis {REDIS_KEY_VERIFIED}: 共 {len(all_valid)} 个节点")
        else:
            logger.warning("本次扫描未发现有效节点")

        await self.close()

if __name__ == "__main__":
    scanner = IPScanner()
    asyncio.run(scanner.run())

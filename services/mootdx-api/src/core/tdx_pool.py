"""
TDX 多节点连接池

提供 Round-Robin 负载均衡，将请求分散到多个 TDX 服务器
以突破单节点并发限制，提升全市场采集速度。
"""

import asyncio
import logging
import random
import socket
import os
import sys
from typing import List, Optional, Tuple
import redis.asyncio as redis
from mootdx.quotes import Quotes

# --- Monkey Patch: Force Source IP for TDX Traffic ---
_TDX_BIND_IP = os.getenv("TDX_BIND_IP")
if _TDX_BIND_IP:
    print(f"MonkeyPatch: ACTIVATING PATCH to bind {_TDX_BIND_IP}")
    _OriginalSocket = socket.socket
    class _BoundSocket(_OriginalSocket):
        def connect(self, address):
            # 7709 是标准 TDX 端口
            is_tdx = isinstance(address, tuple) and len(address) >= 2 and address[1] in [7701, 7709, 7711, 7727]
            if is_tdx:
                try:
                    self.bind((_TDX_BIND_IP, 0))
                except Exception as e:
                    print(f"MonkeyPatch: Bind FAILED: {e}")
            super().connect(address)
    socket.socket = _BoundSocket
# --- End Monkey Patch ---

logger = logging.getLogger("tdx-pool")


class TDXClientPool:
    """
    TDX 多节点连接池
    
    通过维护多个 TDX 客户端连接，实现请求的负载均衡。
    每个客户端连接会通过 bestip 自动选择最佳服务器节点。
    """
    
    def __init__(self, size: int = 3):
        """
        初始化连接池
        
        Args:
            size: 连接池大小，默认 3 个连接
        """
        self.size = size
        self.clients: List[Quotes] = []
        self._index = 0
        self._lock = asyncio.Lock()
        self._initialized = False
        self.health_status: List[bool] = []  # True=Healthy, False=Unhealthy
    
    async def initialize(self) -> None:
        """
        初始化所有 TDX 客户端连接
        
        每个客户端会独立执行 bestip 选择，可能连接到不同的服务器节点
        
        使用 double-check locking 模式确保线程安全
        """
        # Fast path: 不需要锁的快速检查
        if self._initialized:
            return
        
        # 获取锁进行初始化
        async with self._lock:
            # Double-check: 可能其他协程已经初始化完成
            if self._initialized:
                return
            
            loop = asyncio.get_event_loop()
            
            logger.info(f"正在初始化 TDX 连接池 (size={self.size})...")
            
            # Configuration Priority:
            # 1. TDX_AUTO_DISCOVER=true (env) -> bestip=True
            # 2. TDX_HOSTS (env) -> Parsed list
            # 3. Code Hardcoded Defaults (Fallback)
            
            auto_discover = os.getenv("TDX_AUTO_DISCOVER", "false").lower() == "true"
            env_hosts = os.getenv("TDX_HOSTS", "")
            
            if auto_discover:
                logger.info("Configuration: Auto-discovery ENABLED (bestip=True)")
                target_server_strategy = 'auto'
            elif env_hosts:
                logger.info(f"Configuration: Using TDX_HOSTS from env: {env_hosts}")
                # Parse "ip:port,ip2:port" string
                parsed_servers = []
                for s in env_hosts.split(','):
                    parts = s.strip().split(':')
                    if len(parts) == 2:
                        parsed_servers.append((parts[0], int(parts[1])))
                target_servers = parsed_servers
                target_server_strategy = 'list'
            else:
                logger.warning("Configuration: No env vars found, using hardcoded fallback list")
                # Fallback list (Updated 2026/01/10)
                target_servers = [
                    ('59.36.5.11', 7709),
                    ('119.147.212.81', 7709),
                    ('124.71.187.122', 7709),
                    ('47.107.64.168', 7709),
                    ('119.29.19.242', 7709),
                    ('123.60.84.66', 7709)
                ]
                target_server_strategy = 'list'

            # Initialize based on strategy
            for i in range(self.size):
                try:
                    if target_server_strategy == 'auto':
                         logger.info(f"  Initializing connection {i+1}/{self.size} (Auto-select)...")
                         client = await loop.run_in_executor(
                            None,
                            lambda: Quotes.factory(market='std', bestip=True)
                        )
                    else:
                        # Round-robin selection from list
                        server = target_servers[i % len(target_servers)]
                        logger.info(f"  Initializing connection {i+1}/{self.size} to {server}...")
                        client = await loop.run_in_executor(
                            None,
                            lambda: Quotes.factory(market='std', bestip=False, server=server)
                        )
                        
                    self.clients.append(client)
                    # Try to extract connected host info
                    try:
                        connected_host = client.client.api.host
                        connected_port = client.client.api.port
                        logger.info(f"  Node {i + 1}/{self.size} connected to {connected_host}:{connected_port}")
                    except:
                        logger.info(f"  Node {i + 1}/{self.size} connected (IP unknown)")
                except Exception as e:
                    logger.error(f"  Node {i + 1} connection failed: {e}")
            
            if len(self.clients) == 0:
                raise RuntimeError("TDX 连接池初始化失败：没有可用的连接")
            
            self.health_status = [True] * len(self.clients)
            self._initialized = True
            logger.info(f"✓ TDX 连接池就绪 ({len(self.clients)}/{self.size} 节点)")
            
            # 启动健康检查后台任务
            asyncio.create_task(self._health_check_loop())
            
            # 启动动态池刷新任务 (Phase 3)
            asyncio.create_task(self._pool_refresh_loop())
    
    async def get_next(self) -> Quotes:
        """
        Round-Robin 获取下一个客户端
        
        使用异步锁确保 _index 的原子性读写操作
        
        Returns:
            下一个可用的 Quotes 客户端
            
        Raises:
            RuntimeError: 如果连接池未初始化或为空
        """
        if not self.clients:
            raise RuntimeError("连接池未初始化或为空")
        
        async with self._lock:
            # 尝试找到一个健康节点
            start_index = self._index
            for i in range(len(self.clients)):
                idx = (start_index + i) % len(self.clients)
                if self.health_status[idx]:
                    self._index = (idx + 1) % len(self.clients)
                    return self.clients[idx]
            
            # 如果全部不健康，强制轮询 (Last Resort)
            # logger.warning("⚠️ 全部节点不健康，强制使用轮询策略")
            client = self.clients[self._index]
            self._index = (self._index + 1) % len(self.clients)
            return client
    
    async def close(self) -> None:
        """
        关闭所有连接
        
        Note: mootdx 客户端没有显式的关闭方法，这里只是清理引用
        """
        async with self._lock:
            self.clients.clear()
            self._initialized = False
            logger.info("TDX 连接池已关闭")
    
    @property
    def active_count(self) -> int:
        """当前活跃连接数"""
        return len(self.clients)
    
    def get_status(self) -> dict:
        """
        获取连接池状态信息
        
        Returns:
            包含连接池状态的字典
        """
        return {
            "pool_size": self.size,
            "active_connections": len(self.clients),
            "initialized": self._initialized,
            "current_index": self._index,
            "health_status": self.health_status
        }
    async def _health_check_loop(self):
        """
        [Reliability Phase 2] 后台健康检查任务
        
        定期对连接池中的 IP 进行探针测试。
        如果探测失败，标记为 UNHEALTHY，get_next 将跳过该节点。
        """
        interval = int(os.getenv("TDX_HEALTH_CHECK_INTERVAL", "60"))
        logger.info(f"🚀 启动健康检查线程 (Interval={interval}s)")
        
        while self._initialized:
            try:
                await asyncio.sleep(interval)
                
                if not self.clients:
                    continue
                    
                loop = asyncio.get_event_loop()
                
                for i, client in enumerate(self.clients):
                    try:
                        # Probe: 获取平安银行(000001)最近1根1分钟K线
                        # 这是一个极轻量的标准请求，用于验证链路和数据完整性
                        data = await loop.run_in_executor(
                            None,
                            lambda: client.bars(category=9, market=0, code='000001', start=0, count=1)
                        )
                        
                        is_healthy = data is not None and len(data) > 0
                        
                        if is_healthy != self.health_status[i]:
                            status_str = "HEALTHY" if is_healthy else "UNHEALTHY"
                            logger.warning(f"🔄 [HealthCheck] Node {i+1} status changed to {status_str}")
                            self.health_status[i] = is_healthy
                        elif not is_healthy:
                             # 持续不健康，记录日志
                             logger.warning(f"⚠️ [HealthCheck] Node {i+1} remains UNHEALTHY")
                            
                    except Exception as e:
                        logger.error(f"❌ [HealthCheck] Node {i+1} probe failed: {e}")
                        if self.health_status[i]:
                             logger.warning(f"⬇️ [HealthCheck] Node {i+1} status changed to UNHEALTHY")
                             self.health_status[i] = False
                             
            except Exception as main_e:
                logger.error(f"Health check loop error: {main_e}")
                await asyncio.sleep(interval) # Prevent spinning on error

    async def _pool_refresh_loop(self):
        """
        [Reliability Phase 3] 动态 IP 池刷新任务
        
        定期 (10分钟) 从 Redis 获取最新的优质 IP列表。
        策略:
        1. 如果发现新 IP 且池子未满 -> 添加
        2. 如果池子满了 -> 尝试替换掉 UNHEALTHY 的节点
        """
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", "")
        
        while self._initialized:
            redis_client = None
            try:
                # 初始等待 1 分钟，之后每 10 分钟刷新一次
                await asyncio.sleep(600)
                
                logger.info("🔄 [PoolRefresh] 开始检查新 IP...")
                address = f"redis://:{redis_password}@{redis_host}:{redis_port}/1"
                redis_client = redis.from_url(address)
                
                candidates = await redis_client.smembers("tdx:verified_ips")
                if not candidates:
                    logger.info("ℹ️ [PoolRefresh] Redis 中无候选 IP")
                    continue
                    
                # 解析 candidates
                new_ips = []
                for c in candidates:
                    try:
                        # redis-py returns bytes if decode_responses=False (default)
                        if isinstance(c, bytes):
                            c = c.decode()
                        ip, port = c.split(':')
                        new_ips.append((ip, int(port)))
                    except Exception as e:
                        logger.warning(f"Failed to parse candidate {c}: {e}")
                
                # 获取当前所有 IP 集合
                current_ips = set()
                
                unhealthy_indices = [i for i, healthy in enumerate(self.health_status) if not healthy]
                
                if unhealthy_indices and new_ips:
                    # 只要有坏节点，就尝试用新 IP 替换
                    idx = unhealthy_indices[0] # 替换第一个坏的
                    candidate = random.choice(new_ips)
                    
                    logger.info(f"♻️ [PoolRefresh] 尝试用 {candidate} 替换坏节点 {idx+1}")
                    
                    loop = asyncio.get_event_loop()
                    new_client = await loop.run_in_executor(
                        None,
                        lambda: Quotes.factory(market='std', bestip=False, server=candidate)
                    )
                    
                    # 验证新客户端
                    try:
                         # 简单验证
                         check = await loop.run_in_executor(
                            None,
                            lambda: new_client.get_security_count(0)
                        )
                         if check is not None:
                             async with self._lock:
                                 self.clients[idx] = new_client
                                 self.health_status[idx] = True # 标记为健康
                             logger.info(f"✅ [PoolRefresh] 节点 {idx+1} 已替换为 {candidate}")
                    except Exception as e:
                        logger.warning(f"❌ [PoolRefresh] 新候选 {candidate} 连接失败: {e}")

            except Exception as e:
                logger.error(f"Pool refresh loop error: {e}")
            finally:
                if redis_client:
                    await redis_client.close()


def get_pool_size() -> int:
    """从环境变量获取连接池大小"""
    return int(os.getenv("TDX_POOL_SIZE", "3"))

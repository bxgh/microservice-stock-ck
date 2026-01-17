"""
TDX 多节点连接池

使用 asyncio.Queue 实现独占式资源管理，确保并发安全。
提供多节点支持，将请求分散到多个 TDX 服务器以突破单节点并发限制。
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
    TDX 多节点连接池 (Thread-Safe Queue Implementation)
    
    使用 asyncio.Queue 管理连接资源，确保每个客户端同一时间只能被一个任务独占使用。
    解决了 pytdx 非线程安全导致的并发数据混乱问题。
    """
    
    def __init__(self, size: int = 3):
        self.size = size
        self.queue = asyncio.Queue() # 资源池
        self._lock = asyncio.Lock()
        self._initialized = False
        self._all_clients = [] # Keep weak ref or list for closing?
    
    async def initialize(self) -> None:
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            loop = asyncio.get_event_loop()
            logger.info(f"正在初始化 TDX 连接池 (Queue Mode, size={self.size})...")
            
            # Env Config
            auto_discover = os.getenv("TDX_AUTO_DISCOVER", "false").lower() == "true"
            env_hosts = os.getenv("TDX_HOSTS", "")
            
            if auto_discover:
                target_server_strategy = 'auto'
            elif env_hosts:
                parsed_servers = []
                for s in env_hosts.split(','):
                    parts = s.strip().split(':')
                    if len(parts) == 2:
                        parsed_servers.append((parts[0], int(parts[1])))
                target_servers = parsed_servers
                target_server_strategy = 'list'
            else:
                target_servers = [
                    ('119.147.212.81', 7709),
                    ('47.107.64.168', 7709),
                    ('119.29.19.242', 7709),
                ]
                target_server_strategy = 'list'

            successful_count = 0
            
            for i in range(self.size):
                try:
                    if target_server_strategy == 'auto':
                         client = await loop.run_in_executor(
                            None, lambda: Quotes.factory(market='std', bestip=True)
                        )
                    else:
                        server = target_servers[i % len(target_servers)]
                        client = await loop.run_in_executor(
                            None, lambda: Quotes.factory(market='std', bestip=False, server=server)
                        )
                        
                    # Put into Queue
                    self.queue.put_nowait(client)
                    self._all_clients.append(client)
                    successful_count += 1
                    
                    try:
                        connected_host = client.client.api.host
                        connected_port = client.client.api.port
                        logger.info(f"  Node {i + 1} conn {connected_host}:{connected_port}")
                    except:
                        pass
                        
                except Exception as e:
                    logger.warning(f"  Node {i + 1} init failed: {e}")
            
            if successful_count == 0:
                logger.error("Pool init failed: 0 connections")
                # Don't raise, let it retry or fail at acquire
            
            self._initialized = True
            logger.info(f"✓ TDX Pool Ready ({successful_count}/{self.size} available)")

    async def acquire(self) -> Quotes:
        """从池中获取一个独占客户端"""
        if not self._initialized:
            await self.initialize()
            
        return await self.queue.get()

    async def release(self, client: Quotes):
        """归还客户端到池中"""
        await self.queue.put(client)

    async def close(self):
        async with self._lock:
            # Drain queue?
            self._initialized = False
            self.queue = asyncio.Queue() # Reset
            # self._all_clients cleanup logic if needed
            logger.info("TDX Pool Closed")

    def get_status(self) -> dict:
        return {
            "pool_size": self.size,
            "available": self.queue.qsize(),
            "initialized": self._initialized
        }

def get_pool_size() -> int:
    return int(os.getenv("TDX_POOL_SIZE", "3"))

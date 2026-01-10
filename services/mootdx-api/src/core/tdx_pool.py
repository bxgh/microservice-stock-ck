"""
TDX 多节点连接池

提供 Round-Robin 负载均衡，将请求分散到多个 TDX 服务器
以突破单节点并发限制，提升全市场采集速度。
"""

import asyncio
import logging
import socket
import os
import sys
from typing import List, Optional
from mootdx.quotes import Quotes

# --- Monkey Patch: Force Source IP for TDX Traffic ---
_TDX_BIND_IP = os.getenv("TDX_BIND_IP")
if _TDX_BIND_IP:
    _OriginalSocket = socket.socket
    class _BoundSocket(_OriginalSocket):
        def connect(self, address):
            # 7709 是标准 TDX 端口
            is_tdx = isinstance(address, tuple) and len(address) >= 2 and address[1] in [7701, 7709, 7711, 7727]
            if is_tdx:
                try:
                    self.bind((_TDX_BIND_IP, 0))
                except Exception as e:
                    # bind 失败通常记录日志但不阻断
                    pass
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
            
            # 预设一组可靠的 TDX 服务器，避免 bestip 扫描导致的高频连接和被封风险
            reliable_servers = [
                ('119.147.212.81', 7709),
                ('124.71.187.122', 7709),
                ('47.107.64.168', 7709),
                ('119.29.19.242', 7709),
                ('123.60.84.66', 7709)
            ]
            
            for i in range(self.size):
                try:
                    server = reliable_servers[i % len(reliable_servers)]
                    print(f"DEBUG: Initializing node {i+1} with server {server}", flush=True)
                    client = await loop.run_in_executor(
                        None,
                        lambda: Quotes.factory(market='std', bestip=False, server=server)
                    )
                    self.clients.append(client)
                    logger.info(f"  节点 {i + 1}/{self.size} 已连接 ({server[0]})")
                except Exception as e:
                    logger.error(f"  节点 {i + 1} 连接失败: {e}")
            
            if len(self.clients) == 0:
                raise RuntimeError("TDX 连接池初始化失败：没有可用的连接")
            
            self._initialized = True
            logger.info(f"✓ TDX 连接池就绪 ({len(self.clients)}/{self.size} 节点)")
    
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
            "current_index": self._index
        }


def get_pool_size() -> int:
    """从环境变量获取连接池大小"""
    return int(os.getenv("TDX_POOL_SIZE", "3"))

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
from mootdx.quotes import Quotes
from mootdx.utils import to_data, get_stock_market, get_frequency
from pytdx.hq import TdxHq_API

# --- Monkey Patch: Force Source IP for TDX Traffic ---
_TDX_BIND_IP = os.getenv("TDX_BIND_IP")
if _TDX_BIND_IP:
    print(f"MonkeyPatch: ACTIVATING PATCH to bind {_TDX_BIND_IP}")
    _OriginalSocket = socket.socket
    class _BoundSocket(_OriginalSocket):
        def connect(self, address):
            # 7701, 7709, 7711, 7727 是标准 TDX 端口
            is_tdx = isinstance(address, tuple) and len(address) >= 2 and address[1] in [7701, 7709, 7711, 7727]
            if is_tdx:
                try:
                    # 允许地址重用，防止大量 TIME_WAIT 导致端口耗尽
                    self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.bind((_TDX_BIND_IP, 0))
                except Exception as e:
                    print(f"MonkeyPatch: Bind FAILED: {e}")
            super().connect(address)
    socket.socket = _BoundSocket
# --- End Monkey Patch ---

logger = logging.getLogger("tdx-pool")

class RobustQuotes:
    """
    Robust wrapper for TdxHq_API to bypass mootdx initialization issues and provide standardized interface.
    Implements mootdx Quotes interface via composition over PyTDX.
    """
    def __init__(self, server=None, timeout=15, **kwargs):
        self.server = server
        self.timeout = timeout
        ip, port = self.server
        
        # Direct initialization of TdxHq_API
        self.client = TdxHq_API(auto_retry=True, raise_exception=True)
        try:
            self.client.connect(ip, int(port), time_out=timeout)
        except Exception as e:
            logger.error(f"RobustQuotes connect failed to {ip}:{port} : {e}")
            raise

    def close(self):
        try:
            if hasattr(self, 'client') and self.client:
                self.client.close()
        except Exception:
            # Ignore errors during close (e.g. TdxConnectionError if already disconnected)
            pass

    def __del__(self):
        self.close()

    @property
    def api(self):
         # Helper for watchdog logging
         return self.client.api if hasattr(self.client, 'api') else None

    # --- Mootdx Interface Implementation ---

    def quotes(self, symbol=None):
        symbol = symbol or []
        if isinstance(symbol, str): 
             symbol = [symbol]
        
        params = []
        for s in symbol:
             m, c = self._clean_symbol(s)
             params.append((m, c))
        
        data = self.client.get_security_quotes(params)
        return to_data(data, symbol=symbol, client=self)
        
    def _clean_symbol(self, symbol):
        s = str(symbol).upper()
        
        # 1. 优先从前后缀提取市场 ID (1=上海, 0=深圳, 2=北京)
        m = None
        if '.SH' in s or s.startswith('SH'):
            m = 1
        elif '.SZ' in s or s.startswith('SZ'):
            m = 0
        elif '.BJ' in s or s.startswith('BJ'):
            m = 2
            
        # 2. 提取 6 位纯数字代码
        c = s.split('.')[0] if '.' in s else s
        c = c[2:] if c.startswith(('SH','SZ','BJ')) else c
        # 防御性：确保 c 是纯数字并补齐 6 位
        c = "".join(filter(str.isdigit, c))
        if len(c) < 6:
            c = c.zfill(6)
            
        # 3. 如果没能从前后缀识别，则使用 mootdx 原生逻辑推断
        if m is None:
            m = get_stock_market(c)
            
        return m, c

    def transaction(self, symbol, start=0, offset=800, **kwargs):
        m, c = self._clean_symbol(symbol)
        data = self.client.get_transaction_data(m, c, start, offset)
        return to_data(data, symbol=symbol, client=self)

    def transactions(self, symbol, date, start=0, offset=800, **kwargs):
        m, c = self._clean_symbol(symbol)
        data = self.client.get_history_transaction_data(m, c, start, offset, int(date))
        return to_data(data, symbol=symbol, client=self)
        
    def bars(self, frequency, symbol, start=0, offset=800, **kwargs):
        if isinstance(frequency, str):
             frequency = get_frequency(frequency)
        m, c = self._clean_symbol(symbol)
        
        data = self.client.get_instrument_bars(frequency, m, c, start, offset)
        return to_data(data, symbol=symbol, client=self)
        
    def index_bars(self, symbol, frequency, start=0, offset=800, **kwargs):
        if isinstance(frequency, str):
             frequency = get_frequency(frequency)
        m, c = self._clean_symbol(symbol)
        
        data = self.client.get_index_bars(frequency, m, c, start, offset)
        return to_data(data, symbol=symbol, client=self)

    def finance(self, symbol):
         m, c = self._clean_symbol(symbol)
         data = self.client.get_finance_info(m, c)
         return to_data(data, symbol=symbol, client=self)

    def xdxr(self, symbol):
         m, c = self._clean_symbol(symbol)
         data = self.client.get_xdxr_info(m, c)
         return to_data(data, symbol=symbol, client=self)
         
    def stocks(self, market=None):
        # Limited implementation: PyTDX requires iteration to fetch all.
        # Check standard mootdx implementation if critical.
        # For now return empty or simple list if market specific.
        return None 

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
        self._all_clients = [] 
        self._watchdog_task = None
        
        # 服务器配置缓存
        self.target_servers = []
        self.target_server_strategy = 'list'
    
    async def initialize(self) -> None:
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            logger.info(f"正在初始化 TDX 连接池 (Queue Mode, size={self.size})...")
            
            # Env Config
            auto_discover = os.getenv("TDX_AUTO_DISCOVER", "false").lower() == "true"
            env_hosts = os.getenv("TDX_HOSTS", "")
            
            if auto_discover:
                self.target_server_strategy = 'auto'
            elif env_hosts:
                parsed_servers = []
                for s in env_hosts.split(','):
                    parts = s.strip().split(':')
                    if len(parts) == 2:
                        parsed_servers.append((parts[0], int(parts[1])))
                self.target_servers = parsed_servers
                self.target_server_strategy = 'list'
            else:
                self.target_servers = [
                    ('175.6.5.153', 7709),
                    ('175.6.5.154', 7709),
                    ('175.6.5.155', 7709),
                ]
                self.target_server_strategy = 'list'

            successful_count = 0
            
            for i in range(self.size):
                client = await self._create_client_with_retry(i)
                if client:
                    self.queue.put_nowait(client)
                    self._all_clients.append(client)
                    successful_count += 1
            
            if successful_count == 0:
                logger.error("Pool init failed: 0 connections available")
            
            # 启动健康巡检
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())
            
            self._initialized = True
            logger.info(f"✓ TDX Pool Ready ({successful_count}/{self.size} available)")

    async def _create_client_with_retry(self, index: int) -> Optional[Quotes]:
        """创建单个 TDX 客户端，带策略路由"""
        loop = asyncio.get_event_loop()
        try:
            if self.target_server_strategy == 'auto':
                # Auto strategy still uses factory which might be buggy, but we prefer list strategy now
                client = await loop.run_in_executor(
                    None, lambda: Quotes.factory(market='std', bestip=True)
                )
            else:
                # 轮换使用目标服务器，增加目的地多样性
                server = self.target_servers[index % len(self.target_servers)]
                # Use RobustQuotes instead of Quotes.factory
                client = await loop.run_in_executor(
                    None, lambda: RobustQuotes(server=server, timeout=15)
                )
            return client
        except Exception as e:
            logger.warning(f"  Node {index + 1} init failed: {e}")
            return None

    async def _watchdog_loop(self):
        """盘中巡检协程：保持连接热度，自动替换坏死连接"""
        logger.info("📡 TDX Pool Watchdog STARTED")
        await asyncio.sleep(30) # 启动后延迟 30s 开始巡检
        
        while True:
            try:
                # 1. 估算巡检窗口
                # 我们逐个检查队列里的空闲客户端
                qsize = self.queue.qsize()
                if qsize > 0:
                    logger.debug(f"🔍 Watchdog: 正在检查 {qsize} 个空闲连接...")
                    
                    for _ in range(qsize):
                        try:
                            # 尝试非阻塞获取，如果获取不到说明正在被使用
                            client = self.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                            
                        # 执行轻量级健康检查 (get_security_count)
                        is_healthy = await self._check_client_health(client)
                        
                        if is_healthy:
                            self.queue.put_nowait(client)
                        else:
                            host = getattr(getattr(client, 'client', None), 'api', None)
                            host_str = f"{getattr(host, 'host', 'unknown')}:{getattr(host, 'port', '0')}"
                            logger.warning(f"♻️ Watchdog: 检测到坏死或响应慢连接 ({host_str}), 正在替换...")
                            
                            # 关闭旧连接
                            try: client.client.close()
                            except: pass
                            if client in self._all_clients:
                                self._all_clients.remove(client)
                            
                            # 随机等待 1-3s 避让，然后建立新连接
                            await asyncio.sleep(random.uniform(1, 3))
                            new_client = await self._create_client_with_retry(random.randint(0, 100))
                            
                            if new_client:
                                self.queue.put_nowait(new_client)
                                self._all_clients.append(new_client)
                                logger.info(f"✅ Watchdog: 已成功替换坏死连接")
                            else:
                                logger.error(f"❌ Watchdog: 替换连接失败，池容量降低")
                
            except Exception as e:
                logger.error(f"⚠️ Watchdog Loop Error: {e}")
            
            # 每 60 秒轮询一次
            await asyncio.sleep(60)

    async def _check_client_health(self, client: Quotes) -> bool:
        """执行轻量级健康检查，返回是否合格"""
        loop = asyncio.get_event_loop()
        start_t = asyncio.get_running_loop().time()
        try:
            # 使用 get_security_count 作为心跳负载
            count = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: client.client.get_security_count(0)),
                timeout=2.0 # 2秒超时即视为不健康（可能被限流或网络抖动）
            )
            elapsed = (asyncio.get_running_loop().time() - start_t) * 1000
            
            if count and count > 0:
                if elapsed > 1000:
                    logger.warning(f"🐢 Watchdog: 节点响应缓慢 ({elapsed:.0f}ms)")
                    # 响应时间超过 1s 的节点虽然能用，但建议后续替换（目前仍判为 True 可视需求调整）
                return True
            return False
        except Exception:
            return False

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
            if self._watchdog_task:
                self._watchdog_task.cancel()
                try: await self._watchdog_task
                except asyncio.CancelledError: pass
                
            self._initialized = False
            self.queue = asyncio.Queue() # Reset
            
            # 关闭所有活跃连接
            for client in self._all_clients:
                try: client.client.close()
                except: pass
            self._all_clients = []
            
            logger.info("TDX Pool Closed")

    def get_status(self) -> dict:
        return {
            "pool_size": self.size,
            "available": self.queue.qsize(),
            "initialized": self._initialized
        }

def get_pool_size() -> int:
    return int(os.getenv("TDX_POOL_SIZE", "3"))

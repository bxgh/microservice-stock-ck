#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mootdx 连接管理器（带连接复用）

Features:
- 自动连接复用（减少创建次数）
- 连接生命周期管理（5分钟自动重建）
- 简单的健康检查
- 异常处理和降级
- 统计信息追踪
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Any

try:
    from mootdx.quotes import Quotes
except ImportError:
    print("错误：无法导入mootdx库，请确保已正确安装")
    print("安装命令：pip install mootdx")
    Quotes = None

try:
    from core.interfaces import ConnectionManagerInterface
except ImportError:
    # 临时兼容，如果接口文件尚未部署
    from abc import ABC, abstractmethod
    class ConnectionManagerInterface(ABC):
        @abstractmethod
        async def initialize(self) -> bool:
            pass

        @abstractmethod
        async def get_connection(self) -> Any:
            pass

        @abstractmethod
        async def release_connection(self, connection: Any) -> None:
            pass

        @abstractmethod
        async def cleanup(self) -> None:
            pass

        @abstractmethod
        def is_healthy(self) -> bool:
            pass

logger = logging.getLogger(__name__)


class MootdxConnection(ConnectionManagerInterface):
    """
    Mootdx 连接管理器（带连接复用）
    
    Features:
    - 自动连接复用（减少创建次数）
    - 连接生命周期管理（5分钟自动重建）
    - 简单的健康检查
    - 异常处理和降级
    """
    
    def __init__(self, 
                 timeout: int = 60, 
                 best_ip: bool = True,
                 connection_lifetime: int = 300,
                 initial_wait_time: float = 0.5,
                 fixed_servers: Optional[list] = None):
        """
        初始化连接管理器
        
        Args:
            timeout: 连接超时时间（秒）
            best_ip: 是否自动选择最佳服务器 (fixed_servers存在时忽略此参数)
            connection_lifetime: 连接生命周期（秒），默认300秒（5分钟）
            initial_wait_time: 连接创建后的初始等待时间（秒），默认0.5秒
            fixed_servers: 固定服务器列表，格式为 ['ip:port', ...] (优先于bestip)
        """
        self.client: Optional[Quotes] = None
        self._connected = False
        self._connect_time: Optional[datetime] = None
        self._connection_lifetime = timedelta(seconds=connection_lifetime)
        
        # 并发保护锁
        self._lock = asyncio.Lock()
        
        self._config = {
            'timeout': timeout,
            'best_ip': best_ip and not fixed_servers,  # 有固定服务器时禁用bestip
            'initial_wait_time': initial_wait_time,
            'fixed_servers': fixed_servers or []
        }
        
        # 统计信息
        self._stats = {
            'total_creates': 0,
            'total_reuses': 0,
            'total_closes': 0,
            'total_failures': 0
        }

    # ========== ConnectionManagerInterface 实现 ==========

    async def initialize(self) -> bool:
        """
        初始化连接管理器
        
        Returns:
            bool: 初始化是否成功
        """
        client = await self.get_client()
        return client is not None

    async def get_connection(self) -> Optional[Quotes]:
        """
        获取一个可用连接
        
        Returns:
            Quotes: Mootdx 客户端实例
        """
        return await self.get_client()

    async def release_connection(self, connection: Any) -> None:
        """
        释放连接
        
        Mootdx 使用单连接模式，不需要显式归还连接。
        """
        pass

    async def cleanup(self) -> None:
        """
        清理所有资源
        """
        async with self._lock:
            await self._close_connection()

    def is_healthy(self) -> bool:
        """
        检查管理器健康状态
        """
        return self._is_connection_healthy()

    # ========== 核心功能实现 ==========
    
    async def get_client(self) -> Optional[Quotes]:
        """
        获取客户端连接（智能复用）
        
        Returns:
            Quotes 客户端实例，如果无法连接则返回 None
        """
        async with self._lock:
            # 1. 无连接或连接已关闭
            if self.client is None or not self._connected:
                return await self._create_connection()
            
            # 2. 连接过期
            if self._is_connection_expired():
                logger.info("Connection expired, recreating...")
                await self._close_connection()
                return await self._create_connection()
            
            # 3. 连接不健康
            if not self._is_connection_healthy():
                logger.warning("Connection unhealthy, recreating...")
                await self._close_connection()
                return await self._create_connection()
            
            # 4. 复用现有连接
            self._stats['total_reuses'] += 1
            logger.debug(f"♻️ Reusing connection (reuses: {self._stats['total_reuses']})")
            return self.client
    
    async def connect(self) -> bool:
        """
        向后兼容的连接方法
        
        Returns:
            bool: 连接是否成功
        """
        return await self.initialize()
    
    def _is_connection_expired(self) -> bool:
        """检查连接是否过期"""
        if self._connect_time is None:
            return True
        
        elapsed = datetime.now() - self._connect_time
        is_expired = elapsed > self._connection_lifetime
        
        if is_expired:
            logger.debug(f"Connection expired (age: {elapsed.total_seconds():.1f}s)")
        
        return is_expired
    
    def _is_connection_healthy(self) -> bool:
        """
        简单的连接健康检查
        
        注意：由于 Mootdx 缺少 ping 接口，这里只做基础检查
        """
        return self._connected and self.client is not None
    
    async def _create_connection(self) -> Optional[Quotes]:
        """创建新连接"""
        if Quotes is None:
            logger.error("❌ mootdx library not installed")
            return None
            
        try:
            logger.info("🔌 Creating new Mootdx connection...")
            
            # 优先使用固定服务器，否则运行bestip获取最佳服务器
            if self._config['fixed_servers']:
                logger.info(f"Using fixed servers: {self._config['fixed_servers']}")
                # 固定服务器模式：直接创建连接，无需bestip
            elif self._config['best_ip']:
                await self._run_bestip()
            
            # 使用成功验证的参数创建连接
            self.client = Quotes.factory(
                market='std',
                multithread=True,
                heartbeat=True,
                block=False
            )
            
            # 等待服务器选择完成（使用配置的等待时间，而非硬编码）
            await asyncio.sleep(self._config['initial_wait_time'])
            
            self._connected = True
            self._connect_time = datetime.now()
            self._stats['total_creates'] += 1
            
            logger.info(f"✅ Connection created (total creates: {self._stats['total_creates']})")
            return self.client
            
        except Exception as e:
            logger.error(f"❌ Failed to create connection: {e}")
            self.client = None
            self._connected = False
            self._connect_time = None
            self._stats['total_failures'] += 1
            return None
    
    async def _run_bestip(self):
        """运行 bestip 获取最佳服务器"""
        try:
            import subprocess
            import sys
            logger.debug("Running bestip to find best server...")
            
            result = subprocess.run(
                [sys.executable, "-m", "mootdx", "bestip"],
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                logger.debug("✅ Best server configured")
            else:
                logger.warning(f"⚠️ bestip warning: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ bestip timeout, using default config")
        except Exception as e:
            logger.warning(f"⚠️ bestip failed: {e}")
    
    async def _close_connection(self):
        """关闭连接"""
        if self.client:
            try:
                # 更具体的异常处理
                if hasattr(self.client, 'close'):
                    self.client.close()
                    logger.debug("Client connection closed successfully")
                else:
                    logger.debug("Client has no close method, cleaning up reference")
            except Exception as e:
                logger.warning(f"⚠️ Connection close error: {e}")
            finally:
                self.client = None
                self._stats['total_closes'] += 1
                logger.debug(f"🔌 Connection closed (total closes: {self._stats['total_closes']})")
        
        self._connected = False
        self._connect_time = None
    
    async def close(self):
        """显式关闭连接（可选）"""
        async with self._lock:
            await self._close_connection()
    
    def get_stats(self) -> dict:
        """获取连接统计信息"""
        if self._stats['total_creates'] == 0:
            reuse_rate = 0.0
        else:
            total_uses = self._stats['total_creates'] + self._stats['total_reuses']
            reuse_rate = (self._stats['total_reuses'] / total_uses) * 100
        
        return {
            **self._stats,
            'reuse_rate': f"{reuse_rate:.1f}%",
            'is_connected': self._connected,
            'connection_age': self._get_connection_age()
        }
    
    def _get_connection_age(self) -> Optional[float]:
        """获取当前连接的年龄（秒）"""
        if self._connect_time is None:
            return None
        return (datetime.now() - self._connect_time).total_seconds()
    
    # ========== 保持向后兼容的方法 ==========
    
    def fetch_transactions(self, symbol: str, date: str, start: int, count: int) -> pd.DataFrame:
        """
        获取分笔数据（同步方法，保持向后兼容）
        
        Args:
            symbol: 股票代码
            date: 日期 (YYYYMMDD)
            start: 起始位置
            count: 获取数量
            
        Returns:
            pd.DataFrame: 分笔数据
        """
        if not self._connected or not self.client:
            return pd.DataFrame()

        try:
            df = self.client.transactions(symbol=symbol, date=date, start=start, count=count)

            if df is None or df.empty:
                return pd.DataFrame()

            return df

        except Exception as e:
            logger.error(f"❌ Failed to fetch transactions: {e}")
            return pd.DataFrame()

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    @property
    def connect_time(self) -> Optional[datetime]:
        """连接时间"""
        return self._connect_time
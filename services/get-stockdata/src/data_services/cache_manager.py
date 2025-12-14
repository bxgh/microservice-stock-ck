# -*- coding: utf-8 -*-
"""
EPIC-007 缓存管理器

统一的缓存管理，支持:
1. 时段感知的 TTL 策略
2. Redis 连接池管理
3. 批量缓存操作
4. 可扩展的缓存后端

@author: EPIC-007 Story 007.02
@date: 2025-12-06
"""

import asyncio
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, time as dt_time
from typing import Any, Dict, List, Optional

import pandas as pd
import redis.asyncio as aioredis

from core.scheduling.calendar_service import CalendarService

logger = logging.getLogger(__name__)


class CacheTTLStrategy(ABC):
    """缓存 TTL 策略抽象基类
    
    支持根据不同条件（时间、数据类型等）动态计算 TTL。
    """
    
    @abstractmethod
    def get_ttl(self, dt: Optional[datetime] = None) -> int:
        """获取 TTL（秒）
        
        Args:
            dt: 时间点，默认为当前时间
            
        Returns:
            int: TTL 秒数
        """
        pass


class TradingAwareTTL(CacheTTLStrategy):
    """交易时段感知的 TTL 策略
    
    根据交易时段动态调整缓存时间:
    - 盘中交易时段 (9:30-15:00): 3秒
    - 盘后 (15:00-次日9:30): 1小时
    - 非交易日: 1天
    """
    
    def __init__(self, calendar: Optional[CalendarService] = None):
        self.calendar = calendar or CalendarService()
        
        # TTL 配置 (秒)
        self.TRADING_TTL = 3  # 盘中 3 秒
        self.AFTER_MARKET_TTL = 3600  # 盘后 1 小时
        self.NON_TRADING_TTL = 86400  # 非交易日 1 天
    
    def get_ttl(self, dt: Optional[datetime] = None) -> int:
        """获取 TTL
        
        Args:
            dt: 时间点，默认为当前时间
            
        Returns:
            int: TTL 秒数
        """
        if dt is None:
            dt = datetime.now()
        
        # 检查是否为交易日
        if not self.calendar.is_trading_day(dt.date()):
            return self.NON_TRADING_TTL
        
        # 检查是否在交易时段
        current_time = dt.time()
        
        # 上午: 09:30 - 11:30
        am_start = dt_time(9, 30)
        am_end = dt_time(11, 30)
        
        # 下午: 13:00 - 15:00
        pm_start = dt_time(13, 0)
        pm_end = dt_time(15, 0)
        
        is_trading = (
            (am_start <= current_time <= am_end) or
            (pm_start <= current_time <= pm_end)
        )
        
        if is_trading:
            return self.TRADING_TTL
        else:
            return self.AFTER_MARKET_TTL


class FixedTTL(CacheTTLStrategy):
    """固定 TTL 策略
    
    简单的固定时间缓存，用于测试或特殊场景。
    """
    
    def __init__(self, ttl: int = 60):
        self.ttl = ttl
    
    def get_ttl(self, dt: Optional[datetime] = None) -> int:
        return self.ttl


class CacheManager:
    """缓存管理器
    
    提供统一的缓存访问接口，支持:
    - 动态 TTL 策略
    - DataFrame 序列化/反序列化
    - 批量操作
    - 自动重连
    
    Example:
        cache = CacheManager(
            redis_url="redis://localhost:6379/0",
            ttl_strategy=TradingAwareTTL()
        )
        await cache.initialize()
        
        # 存储
        await cache.set("quotes:000001", df)
        
        # 读取
        cached_df = await cache.get("quotes:000001")
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_strategy: Optional[CacheTTLStrategy] = None,
        key_prefix: str = "stockdata:",
    ):
        """初始化
        
        Args:
            redis_url: Redis 连接 URL
            ttl_strategy: TTL 策略，默认使用 TradingAwareTTL
            key_prefix: 缓存键前缀，避免键冲突
        """
        # Auto-configure from env if default URL is used or none provided
        if redis_url == "redis://localhost:6379/0":
            host = os.getenv("REDIS_HOST", "localhost")
            port = os.getenv("REDIS_PORT", "6379")
            password = os.getenv("REDIS_PASSWORD", "")
            db = os.getenv("REDIS_DB", "0")
            
            if password:
                redis_url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                redis_url = f"redis://{host}:{port}/{db}"
                
        self.redis_url = redis_url
        self.ttl_strategy = ttl_strategy or TradingAwareTTL()
        self.key_prefix = key_prefix
        
        self._redis: Optional[aioredis.Redis] = None
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> bool:
        """初始化 Redis 连接
        
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if self._initialized:
                return True
            
            try:
                self._redis = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=False,  # 二进制模式，支持 pickle
                    max_connections=10,
                )
                
                # 测试连接
                ping_result = self._redis.ping()
                if asyncio.iscoroutine(ping_result):
                    await ping_result
                
                self._initialized = True
                logger.info(f"CacheManager initialized: {self.redis_url}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize CacheManager: {e}")
                return False
    
    async def close(self) -> None:
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._initialized = False
            logger.info("CacheManager closed")
    
    def _make_key(self, key: str) -> str:
        """生成完整缓存键
        
        Args:
            key: 原始键
            
        Returns:
            str: 带前缀的完整键
        """
        return f"{self.key_prefix}{key}"
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """存储数据
        
        Args:
            key: 缓存键
            value: 值（支持 DataFrame, dict, list 等）
            ttl: TTL 秒数，None 则使用策略计算
            
        Returns:
            bool: 是否成功
        """
        if not self._initialized:
            logger.warning("CacheManager not initialized")
            return False
        
        try:
            full_key = self._make_key(key)
            
            # 序列化
            if isinstance(value, pd.DataFrame):
                # DataFrame 转 JSON
                serialized = value.to_json(orient='split', date_format='iso')
            else:
                serialized = json.dumps(value)
            
            # 计算 TTL
            if ttl is None:
                ttl = self.ttl_strategy.get_ttl()
            
            # 存储
            await self._redis.setex(full_key, ttl, serialized)
            
            logger.debug(f"Cache SET: {key} (TTL={ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache SET failed for {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """读取数据
        
        Args:
            key: 缓存键
            
        Returns:
            Any: 缓存值，不存在返回 None
        """
        if not self._initialized:
            logger.warning("CacheManager not initialized")
            return None
        
        try:
            full_key = self._make_key(key)
            serialized = await self._redis.get(full_key)
            
            if serialized is None:
                logger.debug(f"Cache MISS: {key}")
                return None
            
            # 反序列化
            data = json.loads(serialized)
            
            # 如果是 DataFrame 格式
            if isinstance(data, dict) and 'columns' in data and 'data' in data:
                df = pd.read_json(json.dumps(data), orient='split')
                logger.debug(f"Cache HIT: {key} ({len(df)} rows)")
                return df
            else:
                logger.debug(f"Cache HIT: {key}")
                return data
            
        except Exception as e:
            logger.error(f"Cache GET failed for {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否成功
        """
        if not self._initialized:
            return False
        
        try:
            full_key = self._make_key(key)
            await self._redis.delete(full_key)
            logger.debug(f"Cache DEL: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache DELETE failed for {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否存在
        """
        if not self._initialized:
            return False
        
        try:
            full_key = self._make_key(key)
            return await self._redis.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache EXISTS check failed for {key}: {e}")
            return False
    
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """批量读取
        
        Args:
            keys: 缓存键列表
            
        Returns:
            Dict[str, Any]: 键值对字典
        """
        if not self._initialized or not keys:
            return {}
        
        try:
            full_keys = [self._make_key(k) for k in keys]
            values = await self._redis.mget(full_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        data = json.loads(value)
                        if isinstance(data, dict) and 'columns' in data:
                            result[key] = pd.read_json(json.dumps(data), orient='split')
                        else:
                            result[key] = data
                    except:
                        pass
            
            logger.debug(f"Cache MGET: {len(result)}/{len(keys)} hits")
            return result
            
        except Exception as e:
            logger.error(f"Cache MGET failed: {e}")
            return {}
    
    def generate_hash_key(self, *args, **kwargs) -> str:
        """生成基于参数的哈希键
        
        用于复杂查询的缓存键生成。
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            str: 哈希键
        """
        content = json.dumps({
            'args': args,
            'kwargs': sorted(kwargs.items())
        }, sort_keys=True)
        
        hash_str = hashlib.md5(content.encode()).hexdigest()[:16]
        return hash_str
    
    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有缓存
        
        Args:
            pattern: 键模式（支持 * 通配符）
            
        Returns:
            int: 删除的键数量
        """
        if not self._initialized:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in self._redis.scan_iter(match=full_pattern):
                keys.append(key)
            
            if keys:
                await self._redis.delete(*keys)
            
            logger.info(f"Cleared {len(keys)} cache keys matching '{pattern}'")
            return len(keys)
            
        except Exception as e:
            logger.error(f"Cache CLEAR pattern failed: {e}")
            return 0

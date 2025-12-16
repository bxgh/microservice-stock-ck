#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票代码客户端服务
基于外部API提供股票基础数据获取服务
"""

import asyncio
import aiohttp
import logging
import os
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential

# Timezone constant
CST = ZoneInfo("Asia/Shanghai")

try:
    from ..models.stock_models import (
        StockInfo, ExternalStockResponse, ExternalStockListResponse,
        StockDataAdapter, CacheKeyGenerator, StockFilter
    )
except ImportError:
    # 测试时使用绝对导入
    from models.stock_models import (
        StockInfo, ExternalStockResponse, ExternalStockListResponse,
        StockDataAdapter, CacheKeyGenerator, StockFilter
    )

logger = logging.getLogger(__name__)


class StockCodeClient:
    """股票代码客户端服务"""

    def __init__(self):
        """
        初始化股票代码客户端
        """
        # Default to 8111 (Remote API Port)
        self.base_url = os.getenv("STOCK_API_URL", "http://124.221.80.250:8111/api/v1")
        self.timeout = aiohttp.ClientTimeout(total=30.0) # Increased timeout for large lists
        self.redis_client: Optional[redis.Redis] = None

        # 从环境变量读取Redis配置
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_password = os.getenv("REDIS_PASSWORD", "")
        redis_db = os.getenv("REDIS_DB", "0")

        # 构建Redis URL
        if redis_password:
            self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        else:
            self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        self.memory_cache: Dict[str, Any] = {}
        self.cache_ttl_memory = 600  # 10分钟
        self.cache_ttl_redis = 1800  # 30分钟
        
        # Thread safety: async lock for shared state
        self._http_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()

    async def initialize(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis连接初始化成功")
        except Exception as e:
            logger.warning(f"Redis连接失败，将使用内存缓存: {e}")
            self.redis_client = None

    async def close(self):
        """关闭连接"""
        if self.redis_client:
            await self.redis_client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        发起HTTP请求到外部API
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            API响应数据
        """
        url = f"{self.base_url}{endpoint}"

        # Thread safety: use lock to protect concurrent access
        async with self._http_lock:
            # trust_env=True permits aiohttp to read HTTP_PROXY from env
            async with aiohttp.ClientSession(timeout=self.timeout, trust_env=True) as session:
                try:
                    async with session.get(url, params=params) as response:
                        response.raise_for_status()
                        return await response.json()
                except aiohttp.ClientError as e:
                    logger.error(f"API请求失败 {url}: {e}")
                    raise
                except asyncio.TimeoutError as e:
                    logger.error(f"API请求超时 {url}: {e}")
                    raise

    async def _fetch_stocks_from_mootdx(self) -> List[StockInfo]:
        """
        从本地Mootdx获取股票列表 (通过TCP协议直连通达信服务器)
        
        Returns:
            股票信息列表
        """
        try:
            from mootdx.quotes import Quotes
            from mootdx.consts import MARKET_SH, MARKET_SZ
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            # 在线程池中执行Mootdx调用
            loop = asyncio.get_event_loop()
            
            # 使用列表推导式或循环获取沪深两市数据
            stocks = []
            
            def fetch_mootdx_data():
                client = Quotes.factory('std')
                data_sh = client.stocks(market=MARKET_SH)
                data_sz = client.stocks(market=MARKET_SZ)
                return data_sh, data_sz

            with ThreadPoolExecutor() as executor:
                df_sh, df_sz = await loop.run_in_executor(executor, fetch_mootdx_data)
                
            # 处理上海市场数据 - 使用vectorized operations
            if df_sh is not None and not df_sh.empty:
                codes_sh = df_sh['code'].astype(str).tolist()
                names_sh = df_sh['name'].astype(str).tolist()
                
                stocks.extend([
                    StockInfo(
                        code=code,
                        name=name,
                        exchange="SH",
                        asset_type="stock",
                        is_active=True,
                        industry=None,
                        sector=None
                    )
                    for code, name in zip(codes_sh, names_sh)
                    if code.startswith('6')
                ])

            # 处理深圳市场数据 - 使用vectorized operations
            if df_sz is not None and not df_sz.empty:
                codes_sz = df_sz['code'].astype(str).tolist()
                names_sz = df_sz['name'].astype(str).tolist()
                
                stocks.extend([
                    StockInfo(
                        code=code,
                        name=name,
                        exchange="SZ",
                        asset_type="stock",
                        is_active=True,
                        industry=None,
                        sector=None
                    )
                    for code, name in zip(codes_sz, names_sz)
                    if code.startswith('0') or code.startswith('3')
                ])

            # 处理北京市场 (Mootdx可能混在SZ或SH，或者需要特殊处理，暂时通过代码前缀补全)
            # 北交所通常在扩展行情，这里先略过，或检查代码前缀
            
            logger.info(f"从本地Mootdx获取到 {len(stocks)} 只股票")
            return stocks
            
        except ImportError:
            logger.error("Mootdx库未安装")
            return []
        except (ValueError, KeyError) as e:
            logger.error(f"从本地Mootdx数据解析失败: {e}")
            return []

    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        # 优先从内存缓存获取
        if cache_key in self.memory_cache:
            cached_data = self.memory_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_ttl_memory):
                logger.debug(f"命中内存缓存: {cache_key}")
                return cached_data['data']
            else:
                del self.memory_cache[cache_key]

        # 从Redis缓存获取
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    logger.debug(f"命中Redis缓存: {cache_key}")
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis缓存读取失败: {e}")

        return None

    async def _set_cache(self, cache_key: str, data: Any, ttl: int = None):
        """设置缓存"""
        ttl = ttl or self.cache_ttl_memory

        # Set memory cache with lock
        async with self._cache_lock:
            self.memory_cache[cache_key] = {
                'data': data,
                'timestamp': datetime.now(CST)
            }

        # 设置Redis缓存
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    self.cache_ttl_redis,
                    json.dumps(data, ensure_ascii=False, default=str)
                )
                logger.debug(f"设置Redis缓存: {cache_key}")
            except (redis.RedisError, redis.ConnectionError) as e:
                logger.warning(f"Redis缓存设置失败: {e}")

    async def get_all_stocks(self, limit: int = 1000) -> List[StockInfo]:
        """
        获取全市场股票列表
        
        优先从缓存获取，然后尝试本地akshare（绕过远程API）

        Args:
            limit: 返回数量限制

        Returns:
            股票列表
        """
        cache_key = CacheKeyGenerator.stocks_all()

        # 尝试从缓存获取
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            logger.info(f"从缓存获取到 {len(cached_data)} 只股票")
            return cached_data[:limit]

        # 直接使用本地Mootdx获取（绕过远程API）
        try:
            stocks = await self._fetch_stocks_from_mootdx()
            
            if stocks:
                # 缓存完整数据
                await self._set_cache(cache_key, stocks)
                logger.info(f"从本地Mootdx获取并缓存了 {len(stocks)} 只股票")
                return stocks[:limit]
            else:
                logger.warning("本地Mootdx返回空列表")
                return []

        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            logger.error(f"获取全市场股票列表失败: {e}")
            return []

    async def get_stocks_by_exchange(self, exchange: str) -> List[StockInfo]:
        """
        按交易所获取股票列表

        Args:
            exchange: 交易所代码 (SH/SZ/BJ)

        Returns:
            股票列表
        """
        cache_key = CacheKeyGenerator.stocks_by_exchange(exchange)

        # 尝试从缓存获取
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 从本地akshare获取全部股票，然后按交易所筛选
        try:
            all_stocks = await self.get_all_stocks(limit=10000)
            stocks = [s for s in all_stocks if s.exchange == exchange.upper()]

            # 缓存数据
            await self._set_cache(cache_key, stocks)
            logger.info(f"获取到交易所 {exchange} 的 {len(stocks)} 只股票")

            return stocks

        except Exception as e:
            logger.error(f"获取交易所 {exchange} 股票列表失败: {e}")
            return []

    async def search_stocks(self, query: str, limit: int = 20) -> List[StockInfo]:
        """
        股票搜索

        Args:
            query: 搜索关键词
            limit: 返回数量限制

        Returns:
            搜索结果
        """
        cache_key = CacheKeyGenerator.stock_search(query)

        # 尝试从缓存获取
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data[:limit]

        # 从本地获取全部股票，然后搜索
        try:
            all_stocks = await self.get_all_stocks(limit=10000)
            
            # 模糊搜索（代码或名称包含关键词）
            query_lower = query.lower()
            results = [
                s for s in all_stocks 
                if query_lower in s.code.lower() or query_lower in s.name.lower()
            ]

            # 缓存搜索结果
            await self._set_cache(cache_key, results, ttl=300)  # 搜索结果缓存5分钟

            return results[:limit]

        except Exception as e:
            logger.error(f"搜索股票 '{query}' 失败: {e}")
            return []

    async def get_stock_detail(self, stock_code: str) -> Optional[StockInfo]:
        """
        获取单只股票详情

        Args:
            stock_code: 股票代码

        Returns:
            股票详情，如果不存在返回None
        """
        cache_key = CacheKeyGenerator.stock_detail(stock_code)

        # 尝试从缓存获取
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 从API获取
        try:
            response_data = await self._make_request(f"/stocks/{stock_code}")
            external_stock = ExternalStockResponse(**response_data)
            stock = StockDataAdapter.from_external(external_stock)

            # 缓存数据
            await self._set_cache(cache_key, stock)

            return stock

        except Exception as e:
            logger.error(f"获取股票 {stock_code} 详情失败: {e}")
            return None

    async def get_stock_mappings(self, stock_code: str) -> Optional[Dict[str, str]]:
        """
        获取股票代码映射信息

        Args:
            stock_code: 股票代码

        Returns:
            代码映射字典
        """
        stock = await self.get_stock_detail(stock_code)
        if stock:
            return {
                "standard": stock.code_mappings.standard,
                "tushare": stock.code_mappings.tushare,
                "akshare": stock.code_mappings.akshare,
                "tonghua_shun": stock.code_mappings.tonghua_shun,
                "wind": stock.code_mappings.wind,
                "east_money": stock.code_mappings.east_money
            }
        return None

    async def filter_stocks(self, filters: StockFilter) -> List[StockInfo]:
        """
        按条件筛选股票

        Args:
            filters: 筛选条件

        Returns:
            筛选后的股票列表
        """
        try:
            # 构建查询参数
            params = {}
            if filters.exchange:
                params["exchange"] = filters.exchange
            if filters.asset_type:
                params["security_type"] = filters.asset_type
            if filters.is_active is not None:
                params["is_active"] = filters.is_active
            if filters.name_contains:
                params["name_search"] = filters.name_contains
            params["limit"] = 5000

            response_data = await self._make_request("/stocks", params)

            external_stocks = [
                ExternalStockResponse(**item) for item in response_data.get("items", [])
            ]
            stocks = StockDataAdapter.from_external_list(external_stocks)

            # 应用额外的筛选条件
            if filters.list_date_after:
                stocks = [
                    stock for stock in stocks
                    if stock.list_date and stock.list_date >= filters.list_date_after
                ]

            if filters.list_date_before:
                stocks = [
                    stock for stock in stocks
                    if stock.list_date and stock.list_date <= filters.list_date_before
                ]

            return stocks

        except Exception as e:
            logger.error(f"筛选股票失败: {e}")
            return []

    async def get_cache_status(self) -> Dict[str, Any]:
        """
        获取缓存状态

        Returns:
            缓存状态信息
        """
        status = {
            "memory_cache": {
                "enabled": True,
                "keys_count": len(self.memory_cache),
                "ttl_seconds": self.cache_ttl_memory
            },
            "redis_cache": {
                "enabled": self.redis_client is not None,
                "ttl_seconds": self.cache_ttl_redis
            }
        }

        if self.redis_client:
            try:
                info = await self.redis_client.info()
                status["redis_cache"]["connected"] = True
                status["redis_cache"]["used_memory"] = info.get("used_memory_human", "Unknown")
                status["redis_cache"]["connected_clients"] = info.get("connected_clients", "Unknown")
            except Exception as e:
                status["redis_cache"]["connected"] = False
                status["redis_cache"]["error"] = str(e)

        return status

    async def refresh_cache(self, cache_type: str = "all") -> bool:
        """
        刷新缓存

        Args:
            cache_type: 缓存类型 ("all", "memory", "redis")

        Returns:
            是否成功
        """
        try:
            if cache_type in ["all", "memory"]:
                self.memory_cache.clear()
                logger.info("内存缓存已清空")

            if cache_type in ["all", "redis"] and self.redis_client:
                await self.redis_client.flushdb()
                logger.info("Redis缓存已清空")

            # 预加载热点数据
            await self.get_all_stocks(100)  # 预加载前100只股票

            return True
        except Exception as e:
            logger.error(f"刷新缓存失败: {e}")
            return False


# 全局实例
stock_client_instance = StockCodeClient()
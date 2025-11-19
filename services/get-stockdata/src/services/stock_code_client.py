#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票代码客户端服务
基于外部API提供股票基础数据获取服务
"""

import asyncio
import aiohttp
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import json
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential

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

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        初始化股票代码客户端

        Args:
            redis_url: Redis连接URL
        """
        self.base_url = "http://124.221.80.250:8000/api/v1"
        self.timeout = aiohttp.ClientTimeout(total=5.0)
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = redis_url
        self.memory_cache: Dict[str, Any] = {}
        self.cache_ttl_memory = 600  # 10分钟
        self.cache_ttl_redis = 1800  # 30分钟

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

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                logger.error(f"API请求失败 {url}: {e}")
                raise
            except Exception as e:
                logger.error(f"API请求异常 {url}: {e}")
                raise

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

        # 设置内存缓存
        self.memory_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
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
            except Exception as e:
                logger.warning(f"Redis缓存设置失败: {e}")

    async def get_all_stocks(self, limit: int = 1000) -> List[StockInfo]:
        """
        获取全市场股票列表

        Args:
            limit: 返回数量限制

        Returns:
            股票列表
        """
        cache_key = CacheKeyGenerator.stocks_all()

        # 尝试从缓存获取
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data[:limit]

        # 从API获取
        try:
            params = {"limit": min(limit, 1000)}
            response_data = await self._make_request("/stocks", params)

            external_stocks = [
                ExternalStockResponse(**item) for item in response_data.get("items", [])
            ]
            stocks = StockDataAdapter.from_external_list(external_stocks)

            # 缓存完整数据
            await self._set_cache(cache_key, stocks)

            return stocks[:limit]

        except Exception as e:
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

        # 从API获取
        try:
            params = {"exchange": exchange, "limit": 5000}
            response_data = await self._make_request("/stocks", params)

            external_stocks = [
                ExternalStockResponse(**item) for item in response_data.get("items", [])
            ]
            stocks = StockDataAdapter.from_external_list(external_stocks)

            # 缓存数据
            await self._set_cache(cache_key, stocks)

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

        # 从API获取
        try:
            params = {"name_search": query, "limit": min(limit, 100)}
            response_data = await self._make_request("/stocks", params)

            external_stocks = [
                ExternalStockResponse(**item) for item in response_data.get("items", [])
            ]
            stocks = StockDataAdapter.from_external_list(external_stocks)

            # 缓存搜索结果
            await self._set_cache(cache_key, stocks, ttl=300)  # 搜索结果缓存5分钟

            return stocks[:limit]

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
# -*- coding: utf-8 -*-
"""
EPIC-007 Remote Akshare 数据提供者

通过 HTTP 代理调用部署在腾讯云的 Akshare API 服务
支持:
- 榜单数据 (RANKING)
- 指数成分 (INDEX)
- 财务数据 (FINANCE) - EPIC-002
- 估值数据 (VALUATION) - EPIC-002
- 行业数据 (INDUSTRY) - EPIC-002

@author: EPIC-007
@date: 2025-12-15
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import aiohttp
import pandas as pd

from .base import DataProvider, DataResult, DataType

logger = logging.getLogger(__name__)

class AkshareProvider(DataProvider):
    """远程 Akshare 数据提供者
    
    通过 HTTP API 获取数据，解决本地网络受限问题。
    """
    
    def __init__(
        self,
        priority: Optional[Dict[DataType, int]] = None,
        api_url: Optional[str] = None,
        proxy_url: Optional[str] = None
    ):
        """初始化
        
        Args:
            priority: 自定义优先级
            api_url: API 服务地址 (默认从环境变量获取)
            proxy_url: 代理地址 (默认从环境变量获取)
        """
        # 从环境变量获取配置 (优先使用 PROXY_URL)
        self._api_url = api_url or os.getenv("AKSHARE_API_URL", "http://124.221.80.250:8003")
        self._proxy = proxy_url or os.getenv("PROXY_URL") or os.getenv("HTTP_PROXY")
        
        self._session: Optional[aiohttp.ClientSession] = None
        
        # 默认优先级
        self._priority = priority or {
            DataType.RANKING: 1,
            DataType.INDEX: 1,
            DataType.FINANCE: 1,   # EPIC-002 核心
            DataType.VALUATION: 1, # EPIC-002 核心
            DataType.VALUATION_BAIDU: 1, # EPIC-002 核心 (Baidu)
            DataType.INDUSTRY: 1,   # EPIC-002 核心
            DataType.META: 1
        }
        
    @property
    def name(self) -> str:
        return "akshare_remote"
    
    @property
    def capabilities(self) -> List[DataType]:
        return [
            DataType.RANKING, 
            DataType.INDEX, 
            DataType.FINANCE, 
            DataType.VALUATION,
            DataType.VALUATION_BAIDU,
            DataType.INDUSTRY,
            DataType.META
        ]
    
    @property
    def priority_map(self) -> Dict[DataType, int]:
        return self._priority
    
    async def initialize(self) -> bool:
        """初始化 HTTP 会话"""
        if not self._session:
            # 增加超时时间以适应较慢的远程响应
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info(f"AkshareRemote initialized: URL={self._api_url}, Proxy={self._proxy}")
        return True
    
    async def close(self) -> None:
        """关闭会话"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("AkshareRemote closed")
            
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._session:
                await self.initialize()
                
            async with self._session.get(
                f"{self._api_url}/health",
                proxy=self._proxy
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status") == "healthy"
                    if status:
                        logger.info("AkshareRemote health check: OK")
                    else:
                        logger.warning(f"AkshareRemote health check returned status: {data.get('status')}")
                    return status
                logger.warning(f"AkshareRemote health check HTTP {response.status}")
                return False
        except Exception as e:
            logger.warning(f"AkshareRemote health check failed: {e}")
            return False

    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """通用获取方法"""
        if not self._session:
            await self.initialize()
            
        start_time = time.time()
        
        try:
            # 1. 路由分发
            if data_type == DataType.RANKING:
                return await self._fetch_ranking(**kwargs)
            elif data_type == DataType.INDEX:
                return await self._fetch_index(**kwargs)
            elif data_type == DataType.FINANCE:
                return await self._fetch_finance(**kwargs)
            elif data_type == DataType.VALUATION:
                return await self._fetch_valuation(**kwargs)
            elif data_type == DataType.VALUATION_BAIDU:
                return await self._fetch_valuation_baidu(**kwargs)
            elif data_type == DataType.INDUSTRY:
                return await self._fetch_industry(**kwargs)
            elif data_type == DataType.META:
                return await self._fetch_meta(**kwargs)
            else:
                return DataResult(False, error=f"Unsupported type: {data_type}")
                
        except Exception as e:
            logger.error(f"Fetch error for {data_type}: {e}")
            return DataResult(
                success=False, 
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )

    async def _request_api(self, endpoint: str, params: dict = None) -> Any:
        """执行 API 请求 (含重试)"""
        url = f"{self._api_url}{endpoint}"
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 显式使用代理进行请求
                start = time.time()
                async with self._session.get(
                    url, 
                    params=params, 
                    proxy=self._proxy
                ) as response:
                    latency = (time.time() - start) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 404:
                         # 某些数据找不到是正常的（如非交易日）
                        logger.warning(f"API 404: {url}")
                        return []
                    else:
                        text = await response.text()
                        logger.error(f"API Error {response.status}: {text[:200]}")
                        # 5xx 错误才重试
                        if response.status < 500:
                            raise Exception(f"API Error {response.status}: {text[:200]}")
                            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(f"AkshareRemote attempt {attempt+1}/{max_retries} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    break
                await asyncio.sleep(1 * (attempt + 1))
                
        raise Exception(f"Max retries reached for {url}: {last_error}")

    async def _fetch_ranking(self, ranking_type: str = "hot", **kwargs) -> DataResult:
        """获取榜单"""
        start_time = time.time()
        today = datetime.now().strftime("%Y%m%d")
        
        api_map = {
            "hot": "/api/v1/rank/hot",
            "surge": "/api/v1/rank/surge",
            "limit_up": f"/api/v1/rank/limit_up?date={today}",
            "dragon_tiger": f"/api/v1/rank/dragon_tiger?date={today}"
        }
        
        endpoint = api_map.get(ranking_type)
        if not endpoint:
            # 兼容处理：对于不支持的类型，返回空或错误
            return DataResult(False, error=f"Unsupported ranking: {ranking_type}")
            
        data = await self._request_api(endpoint)
        df = pd.DataFrame(data)
        
        return DataResult(
            success=True,
            data=df,
            latency_ms=(time.time() - start_time) * 1000,
            extra={"source": "remote_api"}
        )

    async def _fetch_index(self, index_code: str = "000300", **kwargs) -> DataResult:
        """获取指数成分"""
        start_time = time.time()
        # 兼容处理：远程 API 使用 symbol 参数
        endpoint = f"/api/v1/index/cons?symbol={index_code}"
        
        data = await self._request_api(endpoint)
        df = pd.DataFrame(data)
        
        return DataResult(
            success=True,
            data=df,
            latency_ms=(time.time() - start_time) * 1000
        )
        
    async def _fetch_finance(self, symbol: str = "", report_type: str = "main", **kwargs) -> DataResult:
        """获取财务数据 (EPIC-002)"""
        start_time = time.time()
        endpoint = f"/api/v1/finance/sheet/{symbol}?type={report_type}"
        
        data = await self._request_api(endpoint)
        df = pd.DataFrame(data)
        
        return DataResult(
            success=True,
            data=df,
            latency_ms=(time.time() - start_time) * 1000
        )

    async def _fetch_valuation(self, symbol: str = "", **kwargs) -> DataResult:
        """获取个股估值数据 (EPIC-002)"""
        start_time = time.time()
        # 远程 API 使用 /api/v1/valuation/{symbol}
        endpoint = f"/api/v1/valuation/{symbol}"
        
        data = await self._request_api(endpoint)
        
        # API 返回字典，转为 DataFrame
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame(data)
            
        return DataResult(
            success=True,
            data=df,
            latency_ms=(time.time() - start_time) * 1000
        )

    async def _fetch_valuation_baidu(self, symbol: str = "", indicator: str = "市盈率(TTM)", **kwargs) -> DataResult:
        """获取百度估值数据 (Robust)"""
        # 注意：云端暂未提供 baidu 端点，保留逻辑但在 kwargs 中处理可能的回退
        start_time = time.time()
        endpoint = f"/api/v1/valuation/baidu/{symbol}"
        params = {"indicator": indicator}
        
        try:
            data = await self._request_api(endpoint, params=params)
            df = pd.DataFrame(data)
            return DataResult(
                success=True,
                data=df,
                latency_ms=(time.time() - start_time) * 1000,
                extra={"source": "baidu", "indicator": indicator}
            )
        except Exception as e:
            logger.warning(f"Baidu valuation failed: {e}")
            return DataResult(False, error=str(e))

    async def _fetch_industry(self, symbol: str = "", **kwargs) -> DataResult:
        """获取行业数据 (EPIC-002)"""
        start_time = time.time()
        
        # 如果提供了 symbol，则获取个股行业信息
        if symbol:
            endpoint = f"/api/v1/industry/stock/{symbol}"
        else:
            # 否则获取行业列表
            endpoint = "/api/v1/industry/list"
            
        data = await self._request_api(endpoint)
        
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame(data)
            
        return DataResult(
            success=True,
            data=df,
            latency_ms=(time.time() - start_time) * 1000
        )

    async def _fetch_meta(self, symbol: str = "", **kwargs) -> DataResult:
        """获取个股元数据 (市值等)"""
        start_time = time.time()
        # Remote Endpoint: /api/v1/stock/info/{symbol}
        endpoint = f"/api/v1/stock/info/{symbol}"
        
        data = await self._request_api(endpoint)
        # API returns dict, wrap in list for DataFrame
        if isinstance(data, dict):
             df = pd.DataFrame([data])
        else:
             df = pd.DataFrame(data)

        return DataResult(
            success=True,
            data=df,
            latency_ms=(time.time() - start_time) * 1000
        )

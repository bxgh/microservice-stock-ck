"""
Cloud API Client Module
HTTP 客户端用于调用云端 API (akshare, baostock, pywencai)
"""
import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional
import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from config import RetryConfig

logger = logging.getLogger("cloud-client")


class CloudAPIClient:
    """统一的云端 API HTTP 客户端"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.proxy = os.getenv("HTTP_PROXY")
        
        # 云端 API 基础 URL
        self.akshare_url = os.getenv("AKSHARE_API_URL", "http://124.221.80.250:8000")
        self.baostock_url = os.getenv("BAOSTOCK_API_URL", "http://124.221.80.250:8001")
        self.pywencai_url = os.getenv("PYWENCAI_API_URL", "http://124.221.80.250:8002")
        
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """初始化 HTTP 会话"""
        async with self._lock:
            if self.session is None:
                timeout = aiohttp.ClientTimeout(total=RetryConfig.CLOUD_API_TIMEOUT)
                self.session = aiohttp.ClientSession(timeout=timeout)
                logger.info(f"Cloud API client initialized with proxy: {self.proxy}")
    
    async def close(self) -> None:
        """关闭 HTTP 会话"""
        async with self._lock:
            if self.session:
                await self.session.close()
                self.session = None
                logger.info("Cloud API client closed")
    
    async def _ensure_session(self) -> None:
        """确保 session 已初始化（线程安全）"""
        if not self.session:
            await self.initialize()
    
    @retry(
        stop=stop_after_attempt(RetryConfig.MAX_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RetryConfig.EXPONENTIAL_MULTIPLIER,
            min=RetryConfig.MIN_WAIT_SECONDS,
            max=RetryConfig.MAX_WAIT_SECONDS
        ),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _fetch(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        通用 HTTP GET 请求（带重试）
        
        Args:
            url: 请求 URL
            params: 查询参数
            
        Returns:
            JSON 响应数据
            
        Raises:
            ValueError: 客户端错误 (4xx)
            ConnectionError: 服务器错误 (5xx)
            asyncio.TimeoutError: 请求超时
        """
        await self._ensure_session()
        
        try:
            async with self.session.get(url, params=params, proxy=self.proxy) as response:
                # 区分客户端错误和服务器错误
                if 400 <= response.status < 500:
                    error_text = await response.text()
                    logger.warning(f"Client error {response.status}: {url}, {error_text}")
                    raise ValueError(f"Invalid request to {url}: HTTP {response.status}")
                
                if 500 <= response.status < 600:
                    error_text = await response.text()
                    logger.error(f"Server error {response.status}: {url}, {error_text}")
                    raise ConnectionError(f"Server unavailable: HTTP {response.status}")
                
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientResponseError as e:
            logger.error(f"HTTP response error: {url}, status={e.status}, message={e.message}")
            raise
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error: {url}, error={e}")
            raise ConnectionError(f"Cannot connect to {url}: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {url}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}", exc_info=True)
            raise
    
    async def fetch_akshare(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        调用 Akshare API
        
        Args:
            endpoint: API 端点 (如 "/api/v1/rank/hot")
            params: 查询参数
        
        Returns:
            pandas DataFrame
        """
        url = f"{self.akshare_url}{endpoint}"
        data = await self._fetch(url, params)
        return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
    
    async def fetch_baostock(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        调用 Baostock API
        
        Args:
            endpoint: API 端点 (如 "/api/v1/history/kline/600519")
            params: 查询参数 (start_date, end_date, frequency, adjust)
        
        Returns:
            pandas DataFrame
        """
        url = f"{self.baostock_url}{endpoint}"
        data = await self._fetch(url, params)
        return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
    
    async def fetch_pywencai(self, query: str, perpage: int = 20) -> pd.DataFrame:
        """
        调用 Pywencai API (自然语言查询)
        
        Args:
            query: 自然语言查询 (如 "今日涨停")
            perpage: 每页数量
        
        Returns:
            pandas DataFrame
        """
        url = f"{self.pywencai_url}/api/v1/query"
        params = {"q": query, "perpage": perpage}
        result = await self._fetch(url, params)
        
        # Pywencai 响应格式: {"data": [...], "cached": bool}
        data = result.get("data", []) if isinstance(result, dict) else result
        return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])

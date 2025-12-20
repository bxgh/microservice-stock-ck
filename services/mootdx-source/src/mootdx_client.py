"""
Mootdx API Client
HTTP 客户端用于调用 mootdx-api 服务
"""
import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from config import RetryConfig

logger = logging.getLogger("mootdx-client")


class MootdxAPIClient:
    """Mootdx API HTTP 客户端"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = os.getenv("MOOTDX_API_URL", "http://mootdx-api:8000")
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """初始化 HTTP 会话"""
        async with self._lock:
            if self.session is None:
                timeout = aiohttp.ClientTimeout(total=RetryConfig.LOCAL_TIMEOUT)
                self.session = aiohttp.ClientSession(timeout=timeout)
                logger.info(f"✓ Mootdx API client initialized: {self.base_url}")
    
    async def close(self) -> None:
        """关闭 HTTP 会话"""
        async with self._lock:
            if self.session:
                await self.session.close()
                self.session = None
                logger.info("Mootdx API client closed")
    
    async def _ensure_session(self) -> None:
        """确保 session 已初始化"""
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
    async def _fetch(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        通用 HTTP GET 请求（带重试）
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    logger.warning(f"API error {response.status}: {url}, {error_text}")
                    raise ValueError(f"API error: HTTP {response.status}")
                
                return await response.json()
                
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error: {url}, error={e}")
            raise ConnectionError(f"Cannot connect to mootdx-api: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {url}")
            raise
    
    async def get_quotes(self, codes: List[str], params: Dict[str, Any]) -> pd.DataFrame:
        """获取实时行情"""
        if not codes:
            return pd.DataFrame()
        
        data = await self._fetch("/api/v1/quotes", {"codes": ",".join(codes)})
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    async def get_tick(self, codes: List[str], params: Dict[str, Any]) -> pd.DataFrame:
        """获取分笔成交"""
        if not codes:
            return pd.DataFrame()
        
        data = await self._fetch(f"/api/v1/tick/{codes[0]}")
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    async def get_history(self, codes: List[str], params: Dict[str, Any]) -> pd.DataFrame:
        """获取历史K线"""
        if not codes:
            return pd.DataFrame()
        
        api_params = {
            "frequency": params.get("frequency", "d"),
            "offset": params.get("offset", 500)
        }
        data = await self._fetch(f"/api/v1/history/{codes[0]}", api_params)
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    async def get_stocks(self, codes: List[str], params: Dict[str, Any]) -> pd.DataFrame:
        """获取股票列表"""
        api_params = {}
        if params.get("market") is not None:
            api_params["market"] = params["market"]
        
        data = await self._fetch("/api/v1/stocks", api_params)
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    async def get_finance_info(self, codes: List[str], params: Dict[str, Any]) -> pd.DataFrame:
        """获取财务基础信息"""
        if not codes:
            return pd.DataFrame()
        
        data = await self._fetch(f"/api/v1/finance/{codes[0]}")
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    async def get_xdxr(self, codes: List[str], params: Dict[str, Any]) -> pd.DataFrame:
        """获取除权除息数据"""
        if not codes:
            return pd.DataFrame()
        
        data = await self._fetch(f"/api/v1/xdxr/{codes[0]}")
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    async def get_index_bars(self, codes: List[str], params: Dict[str, Any]) -> pd.DataFrame:
        """获取指数K线"""
        if not codes:
            return pd.DataFrame()
        
        api_params = {
            "frequency": params.get("frequency", "d"),
            "offset": params.get("offset", 500)
        }
        data = await self._fetch(f"/api/v1/index/bars/{codes[0]}", api_params)
        return pd.DataFrame(data) if data else pd.DataFrame()

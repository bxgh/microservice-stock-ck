"""
云端数据同步基础服务

负责处理 HTTP API 请求、重试机制、代理配置和基础数据清洗。
"""

import logging
import os
import httpx
from typing import Dict, Any, Optional, List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)

class CloudSyncService:
    """
    云端数据同步服务基类
    """
    
    def __init__(self):
        # 1. 代理配置
        self.http_proxy = os.getenv("HTTP_PROXY")
        self.https_proxy = os.getenv("HTTPS_PROXY")
        self.proxies = {}
        if self.http_proxy:
            self.proxies["http://"] = self.http_proxy
        if self.https_proxy:
            self.proxies["https://"] = self.https_proxy
            
        # 2. 从配置获取云端 API URL
        # task.yml 中的 CLOUD_API_URL 可能是基础 URL（如 http://124.221.80.250:8000/api/v1/stocks/all）
        # 但我们这里的 Collector 需要访问不同的端口 (8001, 8002, 8003)
        # 因此，我们在子类中定义具体的 BASE_URL，或者从环境变量读取特定的 URL
        
        # 默认使用内部测试通过的 IP，实际生产应从环境变量读取
        self.cloud_host = os.getenv("CLOUD_HOST", "124.221.80.250")
        
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """初始化 HTTP 客户端"""
        if not self.client:
            self.client = httpx.AsyncClient(
                proxies=self.proxies,
                timeout=30.0,
                trust_env=True
            )
            logger.info(f"CloudSyncService initialized with proxies: {self.proxies}")

    async def close(self):
        """关闭 HTTP 客户端"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("CloudSyncService closed.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, httpx.RemoteProtocolError)),
        reraise=True
    )
    async def _fetch_api(self, url: str, params: Dict[str, Any] = None) -> Any:
        """
        通用 API 请求方法 (带重试)
        
        Args:
            url: 完整 URL 或相对路径
            params: GET 参数
            
        Returns:
            JSON 响应数据 (Dict or List)
        """
        if not self.client:
            await self.initialize()
            
        try:
            logger.debug(f"Fetch API: {url}, params={params}")
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            
            # 尝试解析 JSON
            try:
                data = resp.json()
                return data
            except ValueError:
                logger.error(f"Invalid JSON response from {url}: {resp.text[:200]}")
                return None
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"API Resource not found (404): {url}")
                return None # 404 不重试，直接返回 None
            logger.error(f"HTTP Error {e.response.status_code}: {url}")
            raise e # 其他错误抛出以触发重试
        except Exception as e:
            logger.error(f"Request failed: {url} - {e}")
            raise e

    def _get_service_url(self, port: int, path: str) -> str:
        """构建完整的服务 URL"""
        return f"http://{self.cloud_host}:{port}{path}"

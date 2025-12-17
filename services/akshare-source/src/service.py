import json
import logging
import os
import time
import asyncio
from typing import Any, Dict, List

import aiohttp
import grpc
import pandas as pd

from datasource.v1 import data_source_pb2, data_source_pb2_grpc

logger = logging.getLogger("akshare-service")

class AkShareService(data_source_pb2_grpc.DataSourceServiceServicer):
    def __init__(self):
        # P1-3 Fix: No hardcoded IP fallback - require explicit config
        self.api_url = os.getenv("AKSHARE_API_URL")
        if not self.api_url:
            raise ValueError("AKSHARE_API_URL environment variable must be set")
        
        self.proxy_url = os.getenv("PROXY_URL", "http://192.168.151.18:3128")
        # Configure timeout
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        # 验证代理配置
        if not self.proxy_url:
            logger.warning("PROXY_URL is not set! Remote connections may fail.")
            
    async def _fetch_remote(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        """从远程 API 获取数据 (with timeout and error handling)"""
        url = f"{self.api_url}{endpoint}"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                # 使用显式代理
                async with session.get(url, params=params, proxy=self.proxy_url) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise aiohttp.ClientResponseError(
                            request_info=resp.request_info,
                            history=resp.history,
                            status=resp.status,
                            message=f"Remote API error: {resp.status} - {text}"
                        )
                    return await resp.json()
            except aiohttp.ClientError as e:
                logger.error(f"Request failed: {url}, proxy={self.proxy_url}. Error: {e}")
                raise
            except asyncio.TimeoutError as e:
                logger.error(f"Request timeout: {url}. Error: {e}")
                raise

    async def FetchData(self, request, context):
        """gRPC: 获取数据"""
        start_time = time.time()
        logger.info(f"Received request: type={request.type}, codes={request.codes}")
        
        try:
            data = None
            
            # 1. 龙虎榜 (示例)
            if request.type == data_source_pb2.DATA_TYPE_RANKING:
                # 映射到远程 API 端点 /api/public/stock_lhb_detail_em
                # 参数可能在 request.params 里 (date)
                date = request.params.get("date")
                endpoint = "/api/public/stock_lhb_detail_em" # 假设的端点
                params = {"date": date} if date else {}
                data = await self._fetch_remote(endpoint, params)
                
            # 2. 财务数据
            elif request.type == data_source_pb2.DATA_TYPE_FINANCE:
                code = request.codes[0] # 假设单只股票
                endpoint = f"/api/public/stock_financial_abstract" # 假设端点
                params = {"symbol": code}
                data = await self._fetch_remote(endpoint, params)
                
            else:
                 return data_source_pb2.DataResponse(
                    success=False, 
                    error_message=f"Unsupported type: {request.type}"
                )
            
            latency = int((time.time() - start_time) * 1000)
            
            # 如果 data 是 list/dict，直接转 JSON
            if data:
                json_str = json.dumps(data)
                return data_source_pb2.DataResponse(
                    success=True,
                    json_data=json_str,
                    source_name="akshare-proxy",
                    latency_ms=latency,
                    format="JSON"
                )
            else:
                 return data_source_pb2.DataResponse(
                    success=True,
                    json_data="[]",
                    source_name="akshare-proxy",
                    latency_ms=latency,
                    format="JSON"
                )

        except Exception as e:
            logger.error(f"Error fetching data: {e}", exc_info=True)
            return data_source_pb2.DataResponse(
                success=False,
                error_message=str(e),
                source_name="akshare-proxy"
            )

    async def GetCapabilities(self, request, context):
        return data_source_pb2.Capabilities(
            supported_types=[
                data_source_pb2.DATA_TYPE_RANKING,
                data_source_pb2.DATA_TYPE_FINANCE,
                data_source_pb2.DATA_TYPE_VALUATION
            ],
            priority=80,
            version="1.0.0"
        )
        
    async def HealthCheck(self, request, context):
        """健康检查 - 验证服务自身状态，不依赖远程 API"""
        try:
            # 检查配置是否正确
            if not self.api_url:
                return data_source_pb2.HealthStatus(
                    healthy=False, 
                    message="AKSHARE_API_URL not configured"
                )
            
            # 服务运行正常
            return data_source_pb2.HealthStatus(
                healthy=True, 
                message=f"AkShare service is running (API: {self.api_url})"
            )
        except Exception as e:
            return data_source_pb2.HealthStatus(
                healthy=False, 
                message=f"Health check error: {str(e)}"
            )

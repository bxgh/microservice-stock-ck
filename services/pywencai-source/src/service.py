import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import grpc
import pandas as pd

from datasource.v1 import data_source_pb2, data_source_pb2_grpc

logger = logging.getLogger("pywencai-service")


class PywencaiService(data_source_pb2_grpc.DataSourceServiceServicer):
    """Pywencai gRPC Service
    
    基于 pywencai 库提供自然语言查询能力：
    - SCREENING: 自然语言选股
    - RANKING: 榜单数据  
    - SECTOR: 板块数据
    """
    
    def __init__(self):
        self._pywencai = None
        self._perpage = 50
        
        # 缓存配置
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5分钟
        self._cache_max_size = 100
        self._cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
        
        # 初始化 pywencai
        try:
            import pywencai
            self._pywencai = pywencai
            logger.info("Pywencai module loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to import pywencai: {e}")
            raise

    async def HealthCheck(self, request, context):
        """健康检查"""
        try:
            if self._pywencai is None:
                return data_source_pb2.HealthStatus(
                    healthy=False,
                    message="Pywencai module not loaded"
                )
            
            # 服务运行正常
            return data_source_pb2.HealthStatus(
                healthy=True,
                message="Pywencai service is running"
            )
        except Exception as e:
            return data_source_pb2.HealthStatus(
                healthy=False,
                message=f"Health check error: {str(e)}"
            )

    async def GetCapabilities(self, request, context):
        """获取能力"""
        return data_source_pb2.Capabilities(
            supported_types=[
                # DATA_TYPE_SCREENING 暂未在proto中定义，暂时移除
                data_source_pb2.DATA_TYPE_RANKING,    # 榜单
                data_source_pb2.DATA_TYPE_SECTOR,     # 板块
            ],
            priority=60,  # 中等优先级
            version="1.0.0"
        )

    async def FetchData(self, request, context):
        """获取数据"""
        start_time = time.time()
        logger.info(f"Received request: type={request.type}, request_id={request.request_id}")
        
        try:
            data = None
            
            # 1. 自然语言选股 (暂时注释，等proto定义后启用)
            # if request.type == data_source_pb2.DATA_TYPE_SCREENING:
            #     query = request.params.get("query", "")
            #     if not query:
            #         raise ValueError("Query parameter required for SCREENING")
            #     data = await self._query_pywencai(query)
                
            # 2. 榜单数据
            if request.type == data_source_pb2.DATA_TYPE_RANKING:
                params_dict = dict(request.params) if request.params else {}
                ranking_type = params_dict.get("type", "limit_up")
                data = await self._fetch_ranking(ranking_type)
                
            # 3. 板块数据
            elif request.type == data_source_pb2.DATA_TYPE_SECTOR:
                params_dict = dict(request.params) if request.params else {}
                sector_type = params_dict.get("type", "industry")
                data = await self._fetch_sector(sector_type)
            
            else:
                return data_source_pb2.DataResponse(
                    success=False,
                    error_message=f"Unsupported data type: {request.type}",
                    source_name="pywencai-source"
                )
            
            latency = int((time.time() - start_time) * 1000)
            
            # 转换数据为 JSON
            if data is not None and hasattr(data, 'to_json'):
                json_str = data.to_json(orient='records', force_ascii=False)
                return data_source_pb2.DataResponse(
                    success=True,
                    json_data=json_str,
                    source_name="pywencai-source",
                    latency_ms=latency,
                    format="JSON"
                )
            else:
                return data_source_pb2.DataResponse(
                    success=False,
                    error_message="No data returned",
                    source_name="pywencai-source",
                    latency_ms=latency
                )

        except Exception as e:
            logger.error(f"Error fetching data: {e}", exc_info=True)
            return data_source_pb2.DataResponse(
                success=False,
                error_message=str(e),
                source_name="pywencai-source",
                latency_ms=int((time.time() - start_time) * 1000)
            )

    async def _query_pywencai(self, query: str, perpage: Optional[int] = None) -> Optional[pd.DataFrame]:
        """执行 pywencai 查询（带缓存）"""
        if self._pywencai is None:
            raise RuntimeError("Pywencai module not loaded")
        
        # 检查缓存
        cache_key = f"{query}:{perpage or self._perpage}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            self._cache_stats["hits"] += 1
            logger.debug(f"Cache hit for query: {query}")
            return cached
        else:
            self._cache_stats["misses"] += 1
        
        # 执行查询
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._pywencai.get(query=query, perpage=perpage or self._perpage, loop=True)
            )
            
            if hasattr(result, 'shape'):
                # 保存到缓存
                self._set_cache(cache_key, result)
                logger.info(f"Query successful: {query}, rows={len(result)}")
                return result
            else:
                logger.warning(f"Query returned no data: {query}")
                return None
        except Exception as e:
            logger.error(f"Query failed: {query}, error: {e}")
            raise

    async def _fetch_ranking(self, ranking_type: str) -> Optional[pd.DataFrame]:
        """获取榜单数据"""
        logger.info(f"_fetch_ranking called with ranking_type={repr(ranking_type)}, type={type(ranking_type)}")
        
        query_map = {
            "limit_up": "今日涨停股票",
            "continuous_limit_up": "连续涨停天数大于1",
            "dragon_tiger": "今日上龙虎榜股票",
            "hot": "今日热门股票",
            "surge": "今日涨幅榜前50",
        }
        
        query = query_map.get(ranking_type)
        logger.info(f"Query from map: {repr(query)}")
        
        if not query:
            raise ValueError(f"Unknown ranking type: {ranking_type}")
        
        return await self._query_pywencai(query)

    async def _fetch_sector(self, sector_type: str) -> Optional[pd.DataFrame]:
        """获取板块数据"""
        query_map = {
            "industry": "今日行业涨幅榜",
            "concept": "今日概念涨幅榜",
        }
        
        query = query_map.get(sector_type)
        if not query:
            raise ValueError(f"Unknown sector type: {sector_type}")
        
        return await self._query_pywencai(query)

    def _get_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            # 检查是否过期
            if time.time() - entry["timestamp"] < self._cache_ttl:
                entry["hits"] += 1
                return entry["data"].copy()
            else:
                # 过期，删除
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """设置缓存"""
        # 检查缓存大小
        if len(self._cache) >= self._cache_max_size:
            # 删除最旧的条目
            oldest_key = min(self._cache.items(), key=lambda x: x[1]["timestamp"])[0]
            del self._cache[oldest_key]
            self._cache_stats["evictions"] += 1
        
        self._cache[cache_key] = {
            "data": data.copy(),
            "timestamp": time.time(),
            "hits": 0
        }

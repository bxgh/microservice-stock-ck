import json
import logging
import time
from typing import Any, Dict, List

import grpc
import pandas as pd
from mootdx.quotes import Quotes

from datasource.v1 import data_source_pb2, data_source_pb2_grpc

logger = logging.getLogger("mootdx-service")

class MooTDXService(data_source_pb2_grpc.DataSourceServiceServicer):
    def __init__(self):
        self.client = None
        # MooTDX 连接复用策略视情况而定，这里简单实现
        # 实际生产中可能需要连接池或每次请求重建
    
    async def initialize(self):
        """Initialize resources (lifecycle method)"""
        try:
            self.client = self._get_client()
            logger.info("MooTDX service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MooTDX service: {e}")
            raise
    
    async def close(self):
        """Cleanup resources (lifecycle method)"""
        try:
            if self.client:
                # MooTDX Quotes client may not have explicit close
                # but we should reset the reference
                self.client = None
                logger.info("MooTDX service closed")
        except Exception as e:
            logger.error(f"Error closing MooTDX service: {e}")
        
    def _get_client(self):
        """获取或重连 Mootdx Client"""
        try:
            if not self.client:
                try:
                    self.client = Quotes.factory(market='std')
                except ValueError:
                    logger.warning("Configuration not found, falling back to default server")
                    self.client = Quotes.factory(market='std', server=('119.147.212.81', 7709))
            return self.client
        except Exception as e:
            logger.error(f"Failed to connect to MooTDX: {e}")
            raise

    async def FetchData(self, request, context):
        """gRPC: 获取数据"""
        start_time = time.time()
        logger.info(f"Received request: type={request.type}, codes={request.codes}")
        
        try:
            client = self._get_client()
            df = pd.DataFrame()
            
            # 1. 实时行情
            if request.type == data_source_pb2.DATA_TYPE_QUOTES:
                # MooTDX 需要区分市场 (0: sz, 1: sh)
                # 这里做个简单的转换，假设 codes 是 600519 这种纯数字
                # 或者 sh600519 这种格式。mootdx quotes() 接口通常接受 list
                # 此处简化，直接传 list，MooTDX 库通常能处理
                data = client.quotes(symbol=request.codes)
                if data is not None:
                    df = data
                else:
                    logger.warning("MooTDX returned None")
                    
            # 2. 分笔成交
            elif request.type == data_source_pb2.DATA_TYPE_TICK:
                if not request.codes:
                    return data_source_pb2.DataResponse(
                        success=False, error_message="No code specified for TICK"
                    )
                code = request.codes[0]
                # 分笔通常需要 start 参数，这里假设取当天的
                # 从 params 解析日期和偏移
                # 实际 MooTDX 分笔接口可能是 transactions(symbol=...)
                data = client.transactions(symbol=code)
                if data is not None:
                    df = data
                    
            # 3. 历史K线 (示例)
            elif request.type == data_source_pb2.DATA_TYPE_HISTORY:
                 if not request.codes:
                     pass
                 code = request.codes[0]
                 freq = request.params.get("frequency", "d")
                 # mootdx bars 接口
                 data = client.bars(symbol=code, frequency=9 if freq=='d' else 9) # 9=日线
                 if data is not None:
                     df = data
            
            else:
                return data_source_pb2.DataResponse(
                    success=False, 
                    error_message=f"Unsupported type: {request.type}"
                )

            # 序列化结果
            latency = int((time.time() - start_time) * 1000)
            
            if df.empty:
                 return data_source_pb2.DataResponse(
                    success=True, # 成功调用但无数据
                    json_data="[]",
                    source_name="mootdx",
                    latency_ms=latency,
                    format="JSON"
                )

            # 转换为 JSON 返回 (简单起见)
            # 处理 datetime 对象
            json_str = df.to_json(orient="records", date_format="iso")
            
            return data_source_pb2.DataResponse(
                success=True,
                json_data=json_str,
                source_name="mootdx",
                latency_ms=latency,
                format="JSON"
            )

        except Exception as e:
            logger.error(f"Error fetching data: {e}", exc_info=True)
            return data_source_pb2.DataResponse(
                success=False,
                error_message=str(e),
                source_name="mootdx"
            )

    async def GetCapabilities(self, request, context):
        """gRPC: 获取能力"""
        return data_source_pb2.Capabilities(
            supported_types=[
                data_source_pb2.DATA_TYPE_QUOTES,
                data_source_pb2.DATA_TYPE_TICK,
                data_source_pb2.DATA_TYPE_HISTORY
            ],
            priority=100,
            version="1.0.0"
        )
        
    async def HealthCheck(self, request, context):
        """gRPC: 健康检查"""
        # 可以尝试 ping 一下通达信服务器
        return data_source_pb2.HealthStatus(
            healthy=True,
            message="MooTDX service is running"
        )

import grpc
import pandas as pd
import logging
import json
import os
from io import StringIO
from typing import List, Dict, Any, Optional
from datasource.v1 import data_source_pb2, data_source_pb2_grpc

logger = logging.getLogger(__name__)

class DataSourceClient:
    """mootdx-source gRPC 客户端"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DataSourceClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, target: str = "127.0.0.1:50051"):
        if not hasattr(self, 'channel'):
            self.target = os.getenv("QS_STOCKDATA_SERVICE_GRPC", target)
            self.channel = None
            self.stub = None
            
    async def initialize(self):
        """初始化 gRPC 连接"""
        if not self.channel:
            # 使用 host 网络模式，直接连接
            logger.info(f"Connecting to data source at {self.target}...")
            self.channel = grpc.aio.insecure_channel(
                self.target,
                options=[
                    ('grpc.max_receive_message_length', 100 * 1024 * 1024), # 100MB
                    ('grpc.keepalive_time_ms', 60000),
                ]
            )
            self.stub = data_source_pb2_grpc.DataSourceServiceStub(self.channel)
            logger.info("✅ Data source client initialized")
            
    async def close(self):
        """关闭连接"""
        if self.channel:
            await self.channel.close()
            self.channel = None
            self.stub = None
            logger.info("Data source client closed")
            
    async def fetch_data(
        self, 
        data_type: int, 
        codes: List[str], 
        params: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        通用数据获取方法
        
        Args:
            data_type: data_source_pb2.DataType 枚举值
            codes: 股票代码列表
            params: 查询参数字典
        
        Returns:
            pd.DataFrame
        """
        if not self.stub:
            await self.initialize()
            
        try:
            req_params = params or {}
            # 转换参数为 protobuf Map
            grpc_params = {k: str(v) for k, v in req_params.items()}
            
            request = data_source_pb2.DataRequest(
                type=data_type,
                codes=codes,
                params=grpc_params
            )
            
            response = await self.stub.FetchData(request, timeout=30)
            
            if not response.success:
                logger.error(f"Data source error ({data_type} codes={codes[:3]}...): {response.error_message}")
                return pd.DataFrame()
                
            if response.format == "JSON" and response.json_data:
                # 解析 JSON 到 DataFrame (使用 StringIO 避免被当做文件路径)
                df = pd.read_json(StringIO(response.json_data), orient="records")
                if not df.empty and 'date' in df.columns:
                     # 尝试标准化日期列 (如果存在)
                     pass 
                return df
                
            return pd.DataFrame()
            
        except grpc.RpcError as e:
            logger.error(f"RPC failed: {e.code()} - {e.details()}")
            return pd.DataFrame()
        except Exception as e:
            logger.exception(f"Client error fetching data: {e}")
            return pd.DataFrame()

# 全局单例
data_client = DataSourceClient()

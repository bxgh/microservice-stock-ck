"""
DataSource gRPC Client

Connects to mootdx-source service for all data fetching.
"""
import logging
import os
import asyncio
from typing import List, Dict, Any, Optional
import pandas as pd
import grpc
from datasource.v1 import data_source_pb2, data_source_pb2_grpc
from src.config.settings import settings

logger = logging.getLogger(__name__)


class DataSourceClient:
    """gRPC client for mootdx-source DataSource service"""
    
    def __init__(self, server_url: Optional[str] = None):
        """
        Initialize DataSource client
        
        Args:
            server_url: gRPC server URL (default: from settings.datasource_url)
        """
        self.server_url = server_url or settings.datasource_url
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[data_source_pb2_grpc.DataSourceServiceStub] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize gRPC connection"""
        if self._initialized:
            return
        
        try:
            self.channel = grpc.aio.insecure_channel(
                self.server_url,
                options=[
                    ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
                    ('grpc.max_send_message_length', 100 * 1024 * 1024),
                ]
            )
            self.stub = data_source_pb2_grpc.DataSourceServiceStub(self.channel)
            self._initialized = True
            logger.info(f"✓ Connected to mootdx-source at {self.server_url}")
        except Exception as e:
            logger.error(f"Failed to initialize DataSource client: {e}")
            raise
    
    async def close(self) -> None:
        """Close gRPC connection"""
        if self.channel:
            await self.channel.close()
            self._initialized = False
            logger.info("DataSource client closed")
    
    async def fetch_quotes(self, codes: List[str], params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Fetch real-time quotes
        
        Args:
            codes: List of stock codes
            params: Optional parameters
            
        Returns:
            DataFrame with quote data
        """
        if not self._initialized:
            await self.initialize()
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_QUOTES,
            codes=codes,
            params=params or {}
        )
        
        response = await self.stub.FetchData(request)
        
        if not response.success:
            logger.error(f"FetchData failed: {response.error_message}")
            return pd.DataFrame()
        
        return pd.read_json(response.json_data)
    
    async def fetch_tick(self, code: str, date: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Fetch tick data
        
        Args:
            code: Stock code
            date: Date (YYYYMMDD)
            params: Optional parameters
            
        Returns:
            DataFrame with tick data
        """
        if not self._initialized:
            await self.initialize()
        
        request_params = params or {}
        request_params['date'] = date
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_TICK,
            codes=[code],
            params=request_params
        )
        
        response = await self.stub.FetchData(request)
        
        if not response.success:
            logger.error(f"FetchData failed: {response.error_message}")
            return pd.DataFrame()
        
        return pd.read_json(response.json_data)
    
    async def fetch_history(self, code: str, start_date: str, end_date: str, 
                           frequency: str = "d", adjust: str = "2") -> pd.DataFrame:
        """
        Fetch historical K-line data
        
        Args:
            code: Stock code
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            frequency: Frequency (d/w/m)
            adjust: Adjust type (0=none, 1=forward, 2=backward)
            
        Returns:
            DataFrame with historical data
        """
        if not self._initialized:
            await self.initialize()
        
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'frequency': frequency,
            'adjust': adjust
        }
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_HISTORY,
            codes=[code],
            params=params
        )
        
        response = await self.stub.FetchData(request)
        
        if not response.success:
            logger.error(f"FetchData failed: {response.error_message}")
            return pd.DataFrame()
        
        return pd.read_json(response.json_data)
    
    async def fetch_finance(self, code: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Fetch financial data"""
        if not self._initialized:
            await self.initialize()
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_FINANCE,
            codes=[code],
            params=params or {}
        )
        
        response = await self.stub.FetchData(request)
        
        if not response.success:
            logger.error(f"FetchData failed: {response.error_message}")
            return pd.DataFrame()
        
        return pd.read_json(response.json_data)
    
    async def fetch_valuation(self, code: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Fetch valuation data"""
        if not self._initialized:
            await self.initialize()
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_VALUATION,
            codes=[code],
            params=params or {}
        )
        
        response = await self.stub.FetchData(request)
        
        if not response.success:
            logger.error(f"FetchData failed: {response.error_message}")
            return pd.DataFrame()
        
        return pd.read_json(response.json_data)
    
    async def fetch_ranking(self, ranking_type: str = "limit_up", params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Fetch ranking data"""
        if not self._initialized:
            await self.initialize()
        
        request_params = params or {}
        request_params['ranking_type'] = ranking_type
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_RANKING,
            codes=[],
            params=request_params
        )
        
        response = await self.stub.FetchData(request)
        
        if not response.success:
            logger.error(f"FetchData failed: {response.error_message}")
            return pd.DataFrame()
        
        return pd.read_json(response.json_data)
    
    async def fetch_meta(self, code: str) -> pd.DataFrame:
        """Fetch stock metadata"""
        if not self._initialized:
            await self.initialize()
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_META,
            codes=[code]
        )
        
        response = await self.stub.FetchData(request)
        
        if not response.success:
            logger.error(f"FetchData failed: {response.error_message}")
            return pd.DataFrame()
        
        return pd.read_json(response.json_data)

    async def fetch_sector(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Fetch sector/industry data using natural language query or code"""
        if not self._initialized:
            await self.initialize()
        
        request_params = params or {}
        request_params['query'] = query
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_SECTOR,
            codes=[],
            params=request_params
        )
        
        response = await self.stub.FetchData(request)
        
        if not response.success:
            logger.error(f"FetchData failed: {response.error_message}")
            return pd.DataFrame()
        
        return pd.read_json(response.json_data)
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        if not self._initialized:
            return False
        
        try:
            request = data_source_pb2.Empty()
            response = await self.stub.HealthCheck(request)
            return response.healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global instance
_client: Optional[DataSourceClient] = None
_lock = asyncio.Lock()


async def get_datasource_client() -> DataSourceClient:
    """
    Dependency injection for FastAPI
    
    Returns:
        DataSourceClient instance
    """
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                _client = DataSourceClient()
                await _client.initialize()
    return _client


async def close_datasource_client():
    """Close global client"""
    global _client
    if _client:
        await _client.close()
        _client = None

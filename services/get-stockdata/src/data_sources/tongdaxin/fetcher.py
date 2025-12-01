#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通达信数据源获取器
基于现有TongDaXinClient实现的标准化数据源
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

try:
    from ..base import DataSourceBase
    from ...services.tongdaxin_client import TongDaXinClient
    from ...models.tick_models import TickData, TickDataRequest, TickDataAdapter
    from .adapter import TongDaXinConnectionAdapter
except ImportError:
    from data_sources.base import DataSourceBase
    from services.tongdaxin_client import TongDaXinClient
    from models.tick_models import TickData, TickDataRequest, TickDataAdapter
    # 临时兼容
    TongDaXinConnectionAdapter = None


class TongDaXinDataSource(DataSourceBase):
    """通达信数据源实现"""

    def __init__(self, max_connections: int = 5, timeout: int = 30):
        """
        初始化通达信数据源

        Args:
            max_connections: 最大连接数
            timeout: 连接超时时间
        """
        self.client = TongDaXinClient(max_connections=max_connections, timeout=timeout)
        if TongDaXinConnectionAdapter:
            self.connection_manager = TongDaXinConnectionAdapter(self.client)
        self._connected = False

    async def connect(self) -> bool:
        """
        连接通达信数据源

        Returns:
            bool: 连接是否成功
        """
        try:
            self._connected = await self.client.initialize()
            return self._connected
        except Exception as e:
            self._connected = False
            return False

    async def get_tick_data(self, request: TickDataRequest) -> List[TickData]:
        """
        获取分笔数据

        Args:
            request: 分笔数据请求

        Returns:
            List[TickData]: 分笔数据列表
        """
        if not self._connected:
            await self.connect()

        try:
            response = await self.client.get_tick_data(request)
            if response.success and response.data:
                return response.data
            return []
        except Exception as e:
            return []

    async def get_tick_data_dataframe(self, request: TickDataRequest) -> pd.DataFrame:
        """
        获取分笔数据(DataFrame格式)

        Args:
            request: 分笔数据请求

        Returns:
            pd.DataFrame: 分笔数据DataFrame
        """
        tick_data = await self.get_tick_data(request)
        if not tick_data:
            return pd.DataFrame()

        return TickDataAdapter.to_dataframe(tick_data)

    async def get_status(self) -> Dict[str, Any]:
        """
        获取通达信数据源状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        try:
            if self._connected:
                status = await self.client.get_status()
                return {
                    "connected": self._connected,
                    "source_name": self.source_name,
                    "available_servers": len(status.available_servers),
                    "response_time": status.response_time,
                    "error_message": status.error_message,
                    "is_connected": status.is_connected,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "connected": False,
                    "source_name": self.source_name,
                    "error_message": "Not initialized",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "connected": False,
                "source_name": self.source_name,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def close(self):
        """关闭通达信连接"""
        try:
            await self.client.close()
            self._connected = False
        except Exception:
            pass

    @property
    def source_name(self) -> str:
        """数据源名称"""
        return "tongdaxin"

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected
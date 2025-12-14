#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据源基类
定义所有数据源必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

try:
    from models.tick_models import TickData, TickDataRequest
    from core.interfaces import ConnectionManagerInterface
except ImportError:
    from models.tick_models import TickData, TickDataRequest
    # 临时兼容
    ConnectionManagerInterface = Any


class DataSourceBase(ABC):
    """数据源基类，定义统一接口"""
    
    def __init__(self):
        self.connection_manager: Optional[ConnectionManagerInterface] = None

    @abstractmethod
    async def connect(self) -> bool:
        """
        连接数据源

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    async def get_tick_data(self, request: TickDataRequest) -> List[TickData]:
        """
        获取分笔数据

        Args:
            request: 分笔数据请求

        Returns:
            List[TickData]: 分笔数据列表
        """
        pass

    @abstractmethod
    async def get_tick_data_dataframe(self, request: TickDataRequest) -> pd.DataFrame:
        """
        获取分笔数据(DataFrame格式)

        Args:
            request: 分笔数据请求

        Returns:
            pd.DataFrame: 分笔数据DataFrame
        """
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """
        获取数据源状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        pass

    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """数据源名称"""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """是否已连接"""
        pass
# -*- coding: utf-8 -*-
"""
EPIC-007 数据提供者模块

提供统一的数据源抽象接口和降级链管理。

核心类:
- DataProvider: 数据提供者抽象基类
- DataResult: 标准化数据返回格式
- DataType: 数据类型枚举
- ProviderChain: 降级链管理

Provider 实现:
- MootdxProvider: 实时行情、分笔、K线 (首选)
- EasyquotationProvider: 实时行情 (备选)
- AkshareProvider: 榜单、指数成分
- PywencaiProvider: 自然语言选股、板块
- BaostockProvider: 历史K线 (需proxychains4)

使用示例:
    from src.data_sources.providers import (
        DataProvider, DataResult, DataType, ProviderChain,
        MootdxProvider, EasyquotationProvider
    )
    
    # 创建降级链
    providers = [MootdxProvider(), EasyquotationProvider()]
    chain = ProviderChain(providers, data_type=DataType.QUOTES)
    
    # 获取数据 (自动降级)
    result = await chain.fetch(codes=["000001"])
"""

from .base import DataProvider, DataResult, DataType
from .chain import ProviderChain, ChainStats, ProviderStats

# Provider 实现
from .mootdx_provider import MootdxProvider
from .easyquotation_provider import EasyquotationProvider
from .akshare_provider import AkshareProvider
from .pywencai_provider import PywencaiProvider
from .baostock_provider import BaostockProvider

# 服务管理器
from .manager import DataServiceManager, get_data_service, close_data_service

__all__ = [
    # 核心类
    "DataProvider",
    "DataResult", 
    "DataType",
    "ProviderChain",
    "ChainStats",
    "ProviderStats",
    # Provider 实现
    "MootdxProvider",
    "EasyquotationProvider",
    "AkshareProvider",
    "PywencaiProvider",
    "BaostockProvider",
    # 服务管理器
    "DataServiceManager",
    "get_data_service",
    "close_data_service",
]

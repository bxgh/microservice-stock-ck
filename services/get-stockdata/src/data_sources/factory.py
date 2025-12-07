#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据源工厂
提供统一的数据源创建接口，支持动态切换数据源
"""

from typing import Dict, Any, Optional
from .base import DataSourceBase
from .mootdx.fetcher import MootdxDataSource
from .tongdaxin.fetcher import TongDaXinDataSource

# 数据源配置
DATA_SOURCE_CONFIG = {
    "mootdx": {
        "class": MootdxDataSource,
        "default": True,  # 默认数据源，更稳定
        "timeout": 60,
        "best_ip": True,
        "overlap_ratio": 0.2,
        "batch_size": 800,
        "max_records": 200000,
        "max_consecutive_empty": 5
    },
    "tongdaxin": {
        "class": TongDaXinDataSource,
        "default": False,  # 备用数据源
        "timeout": 30,
        "max_connections": 5
    },
    "akshare": {
        "class": None,  # 未来扩展
        "default": False,
    },
    "tushare": {
        "class": None,  # 未来扩展
        "default": False,
    }
}


class DataSourceFactory:
    """数据源工厂"""

    @staticmethod
    def create_source(source_type: str, config: Optional[Dict[str, Any]] = None) -> DataSourceBase:
        """
        创建数据源实例

        Args:
            source_type: 数据源类型 ('mootdx', 'akshare', 'tushare')
            config: 自定义配置，如果为None则使用默认配置

        Returns:
            DataSourceBase: 数据源实例

        Raises:
            ValueError: 不支持的数据源类型
        """
        if source_type not in DATA_SOURCE_CONFIG:
            raise ValueError(
                f"不支持的数据源: {source_type}。支持的数据源: {list(DATA_SOURCE_CONFIG.keys())}"
            )

        source_config = DATA_SOURCE_CONFIG[source_type]
        source_class = source_config["class"]

        if source_class is None:
            raise ValueError(f"数据源 {source_type} 尚未实现")

        # 合并默认配置和自定义配置
        final_config = {k: v for k, v in source_config.items() if k != 'class'}
        if config:
            final_config.update(config)

        # 过滤掉非构造函数参数
        constructor_params = {}
        constructor_fields = [
            'timeout', 'best_ip', 'overlap_ratio', 'batch_size',
            'max_records', 'max_consecutive_empty', 'max_connections'
        ]
        for field in constructor_fields:
            if field in final_config:
                constructor_params[field] = final_config[field]

        instance = source_class(**constructor_params)
        
        # 注册到监控器
        try:
            from ..core.monitoring.connection_monitor import connection_monitor
            if instance.connection_manager:
                connection_monitor.register(source_type, instance.connection_manager)
        except ImportError:
            # 避免循环导入导致的错误，或者监控模块未准备好
            pass
            
        return instance

    @staticmethod
    def create_default_source() -> DataSourceBase:
        """
        创建默认数据源

        Returns:
            DataSourceBase: 默认数据源实例
        """
        # 找到默认数据源
        for source_type, config in DATA_SOURCE_CONFIG.items():
            if config.get("default", False) and config["class"] is not None:
                return DataSourceFactory.create_source(source_type)

        # 如果没有默认配置，使用第一个可用的
        for source_type, config in DATA_SOURCE_CONFIG.items():
            if config["class"] is not None:
                return DataSourceFactory.create_source(source_type)

        raise ValueError("没有可用的数据源")

    @staticmethod
    def get_available_sources() -> list[str]:
        """
        获取可用的数据源列表

        Returns:
            list[str]: 可用数据源类型列表
        """
        return [
            source_type for source_type, config in DATA_SOURCE_CONFIG.items()
            if config["class"] is not None
        ]

    @staticmethod
    def get_source_config(source_type: str) -> Dict[str, Any]:
        """
        获取数据源配置

        Args:
            source_type: 数据源类型

        Returns:
            Dict[str, Any]: 数据源配置
        """
        if source_type not in DATA_SOURCE_CONFIG:
            raise ValueError(
                f"不支持的数据源: {source_type}"
            )

        return DATA_SOURCE_CONFIG[source_type].copy()
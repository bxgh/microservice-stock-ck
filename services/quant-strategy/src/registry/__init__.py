"""
服务注册模块
"""

from .nacos_registry_simple import (
    initialize_nacos,
    register_to_nacos,
    cleanup_nacos,
    NacosRegistry
)

__all__ = [
    "initialize_nacos",
    "register_to_nacos",
    "cleanup_nacos",
    "NacosRegistry"
]

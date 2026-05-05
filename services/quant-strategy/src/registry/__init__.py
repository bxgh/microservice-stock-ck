"""
服务注册模块
"""

from .nacos_registry_simple import NacosRegistry, cleanup_nacos, initialize_nacos, register_to_nacos

__all__ = [
    "initialize_nacos",
    "register_to_nacos",
    "cleanup_nacos",
    "NacosRegistry"
]

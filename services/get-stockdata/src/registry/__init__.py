"""
服务注册发现模块
"""

from .service_registry import ServiceRegistry, ServiceInstance, get_service_registry, init_service_registry

__all__ = [
    "ServiceRegistry",
    "ServiceInstance",
    "get_service_registry",
    "init_service_registry"
]
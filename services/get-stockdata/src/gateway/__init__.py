# -*- coding: utf-8 -*-
"""
Gateway 包 - 数据源网关

提供统一的 gRPC 数据源访问接口，实现服务发现、降级路由和熔断保护。
"""

from .circuit_breaker import GrpcCircuitBreaker, CircuitState
from .grpc_provider_chain import GrpcProviderChain
from .data_source_gateway import DataSourceGateway

__all__ = [
    "GrpcCircuitBreaker",
    "CircuitState",
    "GrpcProviderChain",
    "DataSourceGateway",
]

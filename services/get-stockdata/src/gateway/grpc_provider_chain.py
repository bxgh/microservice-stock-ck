# -*- coding: utf-8 -*-
"""
gRPC Provider Chain - gRPC 数据源降级链

实现基于 gRPC 的多数据源降级逻辑
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import grpc
from datasource.v1 import data_source_pb2, data_source_pb2_grpc

from .circuit_breaker import GrpcCircuitBreaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)


@dataclass
class GrpcProviderConfig:
    """gRPC Provider 配置"""
    name: str
    address: str  # 例如 "localhost:50051"
    priority: int  # 优先级，数字越小优先级越高
    timeout: float = 5.0  # 请求超时(秒)


@dataclass
class ProviderStats:
    """Provider 统计信息"""
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_error: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests
    
    @property
    def avg_latency_ms(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count


@dataclass
class ChainStats:
    """降级链统计信息"""
    total_requests: int = 0
    primary_success: int = 0
    fallback_success: int = 0
    all_failed: int = 0
    provider_stats: Dict[str, ProviderStats] = field(default_factory=dict)
    
    @property
    def primary_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.primary_success / self.total_requests
    
    @property
    def overall_success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.primary_success + self.fallback_success) / self.total_requests


class GrpcProviderChain:
    """gRPC 数据源降级链
    
    管理多个 gRPC 数据源，实现：
    - 按优先级降级
    - 熔断保护
    - 健康检查
    - 统计信息
    
    Example:
        providers = [
            GrpcProviderConfig("mootdx", "localhost:50051", priority=1),
            GrpcProviderConfig("akshare", "localhost:50052", priority=2),
        ]
        
        chain = GrpcProviderChain(providers, data_source_pb2.DATA_TYPE_QUOTES)
        await chain.initialize()
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_QUOTES,
            codes=["000001", "600519"]
        )
        
        response = await chain.fetch(request)
        print(response.source_name, response.latency_ms)
    """
    
    def __init__(
        self,
        providers: List[GrpcProviderConfig],
        data_type: data_source_pb2.DataType,
        enable_circuit_breaker: bool = True,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        """初始化 gRPC 降级链
        
        Args:
            providers: Provider 配置列表
            data_type: 数据类型
            enable_circuit_breaker: 是否启用熔断器
            circuit_breaker_config: 熔断器配置
        """
        self.data_type = data_type
        self.enable_circuit_breaker = enable_circuit_breaker
        
        # 按优先级排序
        self.providers = sorted(providers, key=lambda p: p.priority)
        
        # gRPC 客户端连接
        self._channels: Dict[str, grpc.aio.Channel] = {}
        self._stubs: Dict[str, data_source_pb2_grpc.DataSourceServiceStub] = {}
        
        # 熔断器
        self._circuit_breakers: Dict[str, GrpcCircuitBreaker] = {}
        if enable_circuit_breaker:
            config = circuit_breaker_config or CircuitBreakerConfig()
            for provider in self.providers:
                self._circuit_breakers[provider.name] = GrpcCircuitBreaker(
                    provider.name, config
                )
        
        # 统计信息
        self._stats = ChainStats()
        for provider in self.providers:
            self._stats.provider_stats[provider.name] = ProviderStats()
        
        # 锁
        self._lock = asyncio.Lock()
        
        logger.info(
            f"GrpcProviderChain initialized for {data_type}: "
            f"{', '.join(p.name + f'(pri={p.priority})' for p in self.providers)}"
        )
    
    async def initialize(self) -> None:
        """初始化 gRPC 连接"""
        for provider in self.providers:
            try:
                channel = grpc.aio.insecure_channel(provider.address)
                self._channels[provider.name] = channel
                self._stubs[provider.name] = data_source_pb2_grpc.DataSourceServiceStub(channel)
                logger.info(f"gRPC channel created for {provider.name} at {provider.address}")
            except Exception as e:
                logger.error(f"Failed to create gRPC channel for {provider.name}: {e}")
    
    async def close(self) -> None:
        """关闭所有 gRPC 连接"""
        for name, channel in self._channels.items():
            try:
                await channel.close()
                logger.info(f"gRPC channel closed for {name}")
            except Exception as e:
                logger.error(f"Error closing gRPC channel for {name}: {e}")
    
    async def fetch(self, request: data_source_pb2.DataRequest) -> data_source_pb2.DataResponse:
        """获取数据，自动降级
        
        Args:
            request: gRPC 数据请求
            
        Returns:
            data_source_pb2.DataResponse: 数据响应
        """
        async with self._lock:
            self._stats.total_requests += 1
        
        for i, provider in enumerate(self.providers):
            # 检查熔断器
            if self.enable_circuit_breaker:
                cb = self._circuit_breakers.get(provider.name)
                if cb and cb.is_open():
                    logger.debug(f"Provider {provider.name} circuit is open, skipping")
                    continue
            
            # 健康检查
            try:
                healthy = await self._health_check(provider)
                if not healthy:
                    logger.debug(f"Provider {provider.name} is unhealthy, skipping")
                    continue
            except Exception as e:
                logger.warning(f"Provider {provider.name} health check failed: {e}")
                continue
            
            # 尝试获取数据
            start_time = time.time()
            try:
                stub = self._stubs.get(provider.name)
                if not stub:
                    logger.error(f"No stub for provider {provider.name}")
                    continue
                
                response = await stub.FetchData(
                    request,
                    timeout=provider.timeout
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                if response.success:
                    # 成功
                    is_fallback = (i > 0)
                    
                    async with self._lock:
                        self._record_success(provider.name, latency_ms, is_fallback)
                    
                    if is_fallback:
                        logger.info(f"Using fallback provider: {provider.name}")
                    
                    return response
                else:
                    # 返回失败
                    logger.debug(f"Provider {provider.name} returned failure: {response.error_message}")
                    async with self._lock:
                        self._record_failure(provider.name, response.error_message, None)
                    
            except grpc.aio.AioRpcError as e:
                latency_ms = (time.time() - start_time) * 1000
                error_msg = f"gRPC error: {e.code()} - {e.details()}"
                logger.warning(f"Provider {provider.name} failed: {error_msg}")
                
                async with self._lock:
                    self._record_failure(provider.name, error_msg, e.code())
                
                continue
            
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                error_msg = f"Unexpected error: {str(e)}"
                logger.warning(f"Provider {provider.name} failed: {error_msg}")
                
                async with self._lock:
                    self._record_failure(provider.name, error_msg, None)
                
                continue
        
        # 所有 Provider 都失败
        async with self._lock:
            self._stats.all_failed += 1
        
        return data_source_pb2.DataResponse(
            success=False,
            error_message="All providers failed"
        )
    
    async def _health_check(self, provider: GrpcProviderConfig) -> bool:
        """健康检查
        
        Args:
            provider: Provider 配置
            
        Returns:
            bool: 是否健康
        """
        try:
            stub = self._stubs.get(provider.name)
            if not stub:
                return False
            
            response = await stub.HealthCheck(
                data_source_pb2.Empty(),
                timeout=2.0
            )
            return response.healthy
        except Exception as e:
            logger.debug(f"Health check failed for {provider.name}: {e}")
            return False
    
    def _record_success(
        self,
        provider_name: str,
        latency_ms: float,
        is_fallback: bool
    ) -> None:
        """记录成功 (需在锁内调用)"""
        if is_fallback:
            self._stats.fallback_success += 1
        else:
            self._stats.primary_success += 1
        
        stats = self._stats.provider_stats.get(provider_name)
        if stats:
            stats.total_requests += 1
            stats.success_count += 1
            stats.total_latency_ms += latency_ms
            stats.last_success = datetime.now()
        
        if self.enable_circuit_breaker:
            cb = self._circuit_breakers.get(provider_name)
            if cb:
                cb.record_success()
    
    def _record_failure(
        self,
        provider_name: str,
        error: str,
        status_code: Optional[grpc.StatusCode]
    ) -> None:
        """记录失败 (需在锁内调用)"""
        stats = self._stats.provider_stats.get(provider_name)
        if stats:
            stats.total_requests += 1
            stats.failure_count += 1
            stats.last_failure = datetime.now()
            stats.last_error = error
        
        if self.enable_circuit_breaker:
            cb = self._circuit_breakers.get(provider_name)
            if cb:
                cb.record_failure(status_code)
    
    def get_stats(self) -> ChainStats:
        """获取统计信息"""
        return self._stats
    
    def get_stats_summary(self) -> Dict:
        """获取统计摘要"""
        return {
            "data_type": self.data_type,
            "total_requests": self._stats.total_requests,
            "primary_success": self._stats.primary_success,
            "fallback_success": self._stats.fallback_success,
            "all_failed": self._stats.all_failed,
            "primary_rate": f"{self._stats.primary_rate:.1%}",
            "overall_success_rate": f"{self._stats.overall_success_rate:.1%}",
            "providers": {
                name: {
                    "success_rate": f"{stats.success_rate:.1%}",
                    "avg_latency_ms": f"{stats.avg_latency_ms:.1f}",
                    "last_error": stats.last_error,
                }
                for name, stats in self._stats.provider_stats.items()
            }
        }
    
    def __repr__(self) -> str:
        providers = ", ".join(p.name for p in self.providers)
        return f"<GrpcProviderChain({self.data_type}) providers=[{providers}]>"

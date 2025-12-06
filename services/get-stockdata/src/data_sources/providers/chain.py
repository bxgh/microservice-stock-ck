# -*- coding: utf-8 -*-
"""
EPIC-007 数据提供者降级链

ProviderChain 管理多个 DataProvider,实现:
1. 按优先级依次尝试数据源
2. 自动跳过不健康的数据源
3. 失败时自动降级到下一个
4. 统计成功/失败率

@author: EPIC-007
@date: 2025-12-06
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base import DataProvider, DataResult, DataType

logger = logging.getLogger(__name__)


@dataclass
class ProviderStats:
    """单个 Provider 的统计信息"""
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_error: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests
    
    @property
    def avg_latency_ms(self) -> float:
        """平均延迟"""
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count


@dataclass
class ChainStats:
    """降级链的统计信息"""
    total_requests: int = 0
    primary_success: int = 0      # 主数据源成功
    fallback_success: int = 0     # 降级成功
    all_failed: int = 0           # 全部失败
    provider_stats: Dict[str, ProviderStats] = field(default_factory=dict)
    
    @property
    def primary_rate(self) -> float:
        """主数据源成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.primary_success / self.total_requests
    
    @property
    def overall_success_rate(self) -> float:
        """整体成功率 (含降级)"""
        if self.total_requests == 0:
            return 0.0
        return (self.primary_success + self.fallback_success) / self.total_requests


class CircuitState:
    """简单的熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class CircuitBreaker:
    """简单的熔断器实现
    
    - 连续失败 N 次后熔断 (OPEN)
    - 熔断 M 秒后进入半开状态 (HALF_OPEN)
    - 半开状态下成功则恢复 (CLOSED), 失败则继续熔断
    """
    failure_threshold: int = 3        # 连续失败阈值
    recovery_timeout: float = 60.0    # 熔断恢复时间 (秒)
    
    state: str = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    
    def record_success(self) -> None:
        """记录成功"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self) -> None:
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def is_open(self) -> bool:
        """检查熔断器是否打开"""
        if self.state == CircuitState.CLOSED:
            return False
        
        if self.state == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker entering half-open state")
                    return False
            return True
        
        # HALF_OPEN 状态允许请求
        return False


class ProviderChain:
    """数据提供者降级链
    
    管理多个 DataProvider, 按优先级依次尝试获取数据。
    
    Features:
    - 按优先级排序 Provider
    - 自动跳过不健康的 Provider
    - 失败时自动降级到下一个
    - 集成熔断器保护
    - 统计各 Provider 的成功/失败率
    
    Example:
        providers = [MootdxProvider(), EasyquotationProvider(), CacheProvider()]
        chain = ProviderChain(providers, data_type=DataType.QUOTES)
        
        result = await chain.fetch(codes=["000001", "600519"])
        print(result)  # DataResult(✅ mootdx/quotes: 2 rows, 50ms)
        
        # 如果 mootdx 失败, 自动降级到 easyquotation
        print(chain.get_stats())
    """
    
    def __init__(
        self,
        providers: List[DataProvider],
        data_type: DataType,
        enable_circuit_breaker: bool = True,
        circuit_failure_threshold: int = 3,
        circuit_recovery_timeout: float = 60.0,
    ):
        """初始化降级链
        
        Args:
            providers: DataProvider 列表
            data_type: 此链处理的数据类型
            enable_circuit_breaker: 是否启用熔断器
            circuit_failure_threshold: 熔断阈值
            circuit_recovery_timeout: 熔断恢复时间
        """
        self._data_type = data_type
        self._enable_circuit_breaker = enable_circuit_breaker
        
        # 过滤支持此数据类型的 Provider, 并按优先级排序
        self._providers = sorted(
            [p for p in providers if p.supports(data_type)],
            key=lambda p: p.get_priority(data_type)
        )
        
        if not self._providers:
            logger.warning(f"ProviderChain for {data_type.value}: no providers available!")
        else:
            names = [f"{p.name}(pri={p.get_priority(data_type)})" for p in self._providers]
            logger.info(f"ProviderChain for {data_type.value}: {', '.join(names)}")
        
        # 为每个 Provider 创建熔断器
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        if enable_circuit_breaker:
            for p in self._providers:
                self._circuit_breakers[p.name] = CircuitBreaker(
                    failure_threshold=circuit_failure_threshold,
                    recovery_timeout=circuit_recovery_timeout
                )
        
        # 统计信息
        self._stats = ChainStats()
        for p in self._providers:
            self._stats.provider_stats[p.name] = ProviderStats()
        
        # 锁
        self._lock = asyncio.Lock()
    
    @property
    def data_type(self) -> DataType:
        """此链处理的数据类型"""
        return self._data_type
    
    @property
    def providers(self) -> List[DataProvider]:
        """Provider 列表 (按优先级排序)"""
        return self._providers
    
    async def fetch(self, **kwargs) -> DataResult:
        """获取数据, 自动降级
        
        按优先级依次尝试 Provider, 直到成功或全部失败。
        
        Args:
            **kwargs: 传递给 Provider.fetch 的参数
        
        Returns:
            DataResult: 包含数据、来源、是否降级等信息
        """
        async with self._lock:
            self._stats.total_requests += 1
        
        for i, provider in enumerate(self._providers):
            # 检查熔断器
            if self._enable_circuit_breaker:
                cb = self._circuit_breakers.get(provider.name)
                if cb and cb.is_open():
                    logger.debug(f"Provider {provider.name} circuit is open, skipping")
                    continue
            
            # 健康检查
            try:
                healthy = await provider.health_check()
                if not healthy:
                    logger.debug(f"Provider {provider.name} is unhealthy, skipping")
                    continue
            except Exception as e:
                logger.warning(f"Provider {provider.name} health check failed: {e}")
                continue
            
            # 尝试获取数据
            start_time = time.time()
            try:
                result = await provider.fetch(self._data_type, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                result.latency_ms = latency_ms
                result.provider = provider.name
                result.data_type = self._data_type
                
                if result.success and not result.is_empty:
                    # 成功
                    result.is_fallback = (i > 0)
                    
                    async with self._lock:
                        self._record_success(provider.name, latency_ms, is_fallback=result.is_fallback)
                    
                    if result.is_fallback:
                        logger.info(f"Using fallback provider: {provider.name}")
                    
                    return result
                else:
                    # 返回成功但数据为空, 视为失败继续尝试
                    logger.debug(f"Provider {provider.name} returned empty data, trying next")
                    
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                logger.warning(f"Provider {provider.name} failed: {e}")
                
                async with self._lock:
                    self._record_failure(provider.name, str(e))
                
                continue
        
        # 所有 Provider 都失败
        async with self._lock:
            self._stats.all_failed += 1
        
        return DataResult(
            success=False,
            data_type=self._data_type,
            error="All providers failed",
            is_fallback=True
        )
    
    def _record_success(self, provider_name: str, latency_ms: float, is_fallback: bool) -> None:
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
        
        if self._enable_circuit_breaker:
            cb = self._circuit_breakers.get(provider_name)
            if cb:
                cb.record_success()
    
    def _record_failure(self, provider_name: str, error: str) -> None:
        """记录失败 (需在锁内调用)"""
        stats = self._stats.provider_stats.get(provider_name)
        if stats:
            stats.total_requests += 1
            stats.failure_count += 1
            stats.last_failure = datetime.now()
            stats.last_error = error
        
        if self._enable_circuit_breaker:
            cb = self._circuit_breakers.get(provider_name)
            if cb:
                cb.record_failure()
    
    def get_stats(self) -> ChainStats:
        """获取统计信息"""
        return self._stats
    
    def get_stats_summary(self) -> Dict:
        """获取统计摘要 (用于监控)"""
        return {
            "data_type": self._data_type.value,
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
    
    async def initialize_all(self) -> Dict[str, bool]:
        """初始化所有 Provider
        
        Returns:
            Dict[str, bool]: Provider 名称 -> 初始化是否成功
        """
        results = {}
        for provider in self._providers:
            try:
                success = await provider.initialize()
                results[provider.name] = success
                if success:
                    logger.info(f"Provider {provider.name} initialized successfully")
                else:
                    logger.warning(f"Provider {provider.name} initialization failed")
            except Exception as e:
                logger.error(f"Provider {provider.name} initialization error: {e}")
                results[provider.name] = False
        return results
    
    async def close_all(self) -> None:
        """关闭所有 Provider"""
        for provider in self._providers:
            try:
                await provider.close()
                logger.info(f"Provider {provider.name} closed")
            except Exception as e:
                logger.error(f"Provider {provider.name} close error: {e}")
    
    def __repr__(self) -> str:
        providers = ", ".join(p.name for p in self._providers)
        return f"<ProviderChain({self._data_type.value}) providers=[{providers}]>"

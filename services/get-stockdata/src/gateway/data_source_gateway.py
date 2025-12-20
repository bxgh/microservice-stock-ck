# -*- coding: utf-8 -*-
"""
Data Source Gateway - 数据源统一网关

提供统一的数据源访问接口，集成：
- 服务发现 (Nacos)
- gRPC Provider Chain
- 降级路由
- 数据源优选

"""

import asyncio
import logging
from typing import Dict, List, Optional

from datasource.v1 import data_source_pb2

from .circuit_breaker import CircuitBreakerConfig
from .grpc_provider_chain import GrpcProviderChain, GrpcProviderConfig

logger = logging.getLogger(__name__)


class DataSourceGateway:
    """数据源统一网关
    
    Features:
    - 管理多个数据类型的 gRPC Provider Chain
    - 支持服务发现（Nacos）
    - 自动降级和熔断保护
    - 数据源优选策略
    
    Example:
        gateway = DataSourceGateway()
        await gateway.initialize()
        
        # 获取行情数据
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_QUOTES,
            codes=["000001", "600519"]
        )
        response = await gateway.fetch(request)
        
        # 获取统计信息
        stats = gateway.get_stats()
    """
    
    def __init__(
        self,
        enable_circuit_breaker: bool = True,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        enable_service_discovery: bool = False,  # TODO: 实现 Nacos 集成
    ):
        """初始化数据源网关
        
        Args:
            enable_circuit_breaker: 是否启用熔断器
            circuit_breaker_config: 熔断器配置
            enable_service_discovery: 是否启用服务发现
        """
        self.enable_circuit_breaker = enable_circuit_breaker
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.enable_service_discovery = enable_service_discovery
        
        # Provider Chain 映射 (data_type -> chain)
        self._chains: Dict[data_source_pb2.DataType, GrpcProviderChain] = {}
        
        # Provider 配置 (硬编码，后续可从 Nacos 动态获取)
        self._provider_configs = self._build_provider_configs()
        
        # 锁
        self._lock = asyncio.Lock()
        
        logger.info("DataSourceGateway initialized")
    
    def _build_provider_configs(self) -> Dict[data_source_pb2.DataType, List[GrpcProviderConfig]]:
        """构建 Provider 配置
        
        统一路由到 mootdx-source 容器，由其内部进行混合架构分发：
        - Local: mootdx (TCP), easyquotation (HTTP)
        - Cloud: akshare, baostock, pywencai (Remote APIs)
        
        Returns:
            Dict: 数据类型 -> Provider 配置列表
        """
        # 统一的数据源配置
        unified_source = GrpcProviderConfig(
            name="unified-source",
            address="localhost:50051",
            priority=1,
            timeout=30.0  # 增加超时以支持云端长连接请求
        )
        
        # 所有数据类型均路由到此统一服务
        configs = {
            data_source_pb2.DATA_TYPE_QUOTES: [unified_source],
            data_source_pb2.DATA_TYPE_TICK: [unified_source],
            data_source_pb2.DATA_TYPE_HISTORY: [unified_source],
            data_source_pb2.DATA_TYPE_RANKING: [unified_source],
            data_source_pb2.DATA_TYPE_SECTOR: [unified_source],
            data_source_pb2.DATA_TYPE_SCREENING: [unified_source],
            data_source_pb2.DATA_TYPE_FINANCE: [unified_source],
            data_source_pb2.DATA_TYPE_VALUATION: [unified_source],
            data_source_pb2.DATA_TYPE_INDUSTRY: [unified_source],
        }
        
        return configs
    
    async def initialize(self) -> None:
        """初始化网关
        
        创建所有数据类型的 Provider Chain 并初始化 gRPC 连接
        """
        logger.info("Initializing DataSourceGateway...")
        
        for data_type, provider_configs in self._provider_configs.items():
            if not provider_configs:
                continue
            
            chain = GrpcProviderChain(
                providers=provider_configs,
                data_type=data_type,
                enable_circuit_breaker=self.enable_circuit_breaker,
                circuit_breaker_config=self.circuit_breaker_config,
            )
            
            await chain.initialize()
            self._chains[data_type] = chain
            
            logger.info(f"Initialized chain for {data_type}: {len(provider_configs)} providers")
        
        logger.info(f"DataSourceGateway initialized with {len(self._chains)} chains")
    
    async def close(self) -> None:
        """关闭网关
        
        关闭所有 gRPC 连接
        """
        logger.info("Closing DataSourceGateway...")
        
        for data_type, chain in self._chains.items():
            try:
                await chain.close()
                logger.info(f"Closed chain for {data_type}")
            except Exception as e:
                logger.error(f"Error closing chain for {data_type}: {e}")
        
        logger.info("DataSourceGateway closed")
    
    async def fetch(self, request: data_source_pb2.DataRequest) -> data_source_pb2.DataResponse:
        """获取数据
        
        根据请求类型自动选择对应的 Provider Chain
        
        Args:
            request: gRPC 数据请求
            
        Returns:
            data_source_pb2.DataResponse: 数据响应
        """
        data_type = request.type
        
        # 获取对应的 Chain
        chain = self._chains.get(data_type)
        if not chain:
            error_msg = f"No provider chain configured for data type: {data_type}"
            logger.error(error_msg)
            return data_source_pb2.DataResponse(
                success=False,
                error_message=error_msg
            )
        
        # 通过 Chain 获取数据
        try:
            response = await chain.fetch(request)
            return response
        except Exception as e:
            error_msg = f"Gateway fetch error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return data_source_pb2.DataResponse(
                success=False,
                error_message=error_msg
            )
    
    def get_stats(self) -> Dict:
        """获取所有 Chain 的统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {}
        for data_type, chain in self._chains.items():
            stats[str(data_type)] = chain.get_stats_summary()
        return stats
    
    def get_chain(self, data_type: data_source_pb2.DataType) -> Optional[GrpcProviderChain]:
        """获取指定数据类型的 Provider Chain
        
        Args:
            data_type: 数据类型
            
        Returns:
            GrpcProviderChain: Provider Chain，不存在则返回 None
        """
        return self._chains.get(data_type)
    
    async def refresh_service_discovery(self) -> None:
        """刷新服务发现
        
        TODO: 从 Nacos 重新获取服务地址并更新 Provider 配置
        """
        if not self.enable_service_discovery:
            logger.debug("Service discovery is disabled")
            return
        
        logger.warning("Service discovery refresh not implemented yet")
        # TODO: 实现 Nacos 集成
        # 1. 从 Nacos 获取所有数据源微服务的地址
        # 2. 更新 _provider_configs
        # 3. 重新创建 Provider Chains
    
    def __repr__(self) -> str:
        return f"<DataSourceGateway(chains={len(self._chains)})>"

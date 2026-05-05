# -*- coding: utf-8 -*-
"""
DataSourceGateway 测试

测试 gRPC 网关的基本功能
"""

import asyncio
import pytest
from datasource.v1 import data_source_pb2

from src.gateway import DataSourceGateway, GrpcProviderConfig, GrpcProviderChain


class TestCircuitBreaker:
    """测试熔断器"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_basic(self):
        """测试熔断器基本功能"""
        from src.gateway.circuit_breaker import GrpcCircuitBreaker, CircuitState
        
        cb = GrpcCircuitBreaker("test-service")
        
        # 初始状态应该是 CLOSED
        assert cb.get_state() == CircuitState.CLOSED
        assert not cb.is_open()
        
        # 记录失败
        for _ in range(5):
            cb.record_failure()
        
        # 应该触发熔断
        assert cb.get_state() == CircuitState.OPEN
        assert cb.is_open()
        
        # 记录成功不应该立即恢复（需要等待恢复时间）
        cb.record_success()
        assert cb.get_state() == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self):
        """测试熔断器重置"""
        from src.gateway.circuit_breaker import GrpcCircuitBreaker, CircuitState
        
        cb = GrpcCircuitBreaker("test-service")
        
        # 触发熔断
        for _ in range(5):
            cb.record_failure()
        assert cb.get_state() == CircuitState.OPEN
        
        # 重置
        cb.reset()
        assert cb.get_state() == CircuitState.CLOSED
        assert not cb.is_open()


class TestGrpcProviderChain:
    """测试 gRPC Provider Chain"""
    
    @pytest.mark.asyncio
    async def test_chain_initialization(self):
        """测试 Chain 初始化"""
        providers = [
            GrpcProviderConfig("mootdx", "localhost:50051", priority=1),
            GrpcProviderConfig("akshare", "localhost:50052", priority=2),
        ]
        
        chain = GrpcProviderChain(
            providers=providers,
            data_type=data_source_pb2.DATA_TYPE_QUOTES
        )
        
        # 检查排序
        assert chain.providers[0].name == "mootdx"
        assert chain.providers[1].name == "akshare"
        
        # 初始化
        await chain.initialize()
        
        # 清理
        await chain.close()


class TestDataSourceGateway:
    """测试 DataSourceGateway"""
    
    @pytest.mark.asyncio
    async def test_gateway_initialization(self):
        """测试网关初始化"""
        gateway = DataSourceGateway()
        await gateway.initialize()
        
        # 检查 chains 是否创建
        assert len(gateway._chains) > 0
        
        # 检查特定数据类型的 chain
        quotes_chain = gateway.get_chain(data_source_pb2.DATA_TYPE_QUOTES)
        assert quotes_chain is not None
        assert len(quotes_chain.providers) > 0
        
        # 清理
        await gateway.close()
    
    @pytest.mark.asyncio
    async def test_gateway_stats(self):
        """测试网关统计信息"""
        gateway = DataSourceGateway()
        await gateway.initialize()
        
        # 获取统计信息
        stats = gateway.get_stats()
        assert isinstance(stats, dict)
        assert len(stats) > 0
        
        # 清理
        await gateway.close()


if __name__ == "__main__":
    # 运行简单测试
    async def main():
        print("Testing Circuit Breaker...")
        test = TestCircuitBreaker()
        await test.test_circuit_breaker_basic()
        await test.test_circuit_breaker_reset()
        print("✓ Circuit Breaker tests passed")
        
        print("\nTesting GrpcProviderChain...")
        test = TestGrpcProviderChain()
        await test.test_chain_initialization()
        print("✓ GrpcProviderChain tests passed")
        
        print("\nTesting DataSourceGateway...")
        test = TestDataSourceGateway()
        await test.test_gateway_initialization()
        await test.test_gateway_stats()
        print("✓ DataSourceGateway tests passed")
        
        print("\n✅ All tests passed!")
    
    asyncio.run(main())

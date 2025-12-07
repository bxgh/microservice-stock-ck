import pytest
import asyncio
from src.data_sources.factory import DataSourceFactory
from src.core.interfaces import ConnectionManagerInterface

class TestUnifiedInterfaceIntegration:
    """测试统一接口集成"""
    
    @pytest.mark.asyncio
    async def test_mootdx_has_connection_manager(self):
        """测试 Mootdx 数据源拥有 connection_manager"""
        source = DataSourceFactory.create_source('mootdx')
        
        assert source.connection_manager is not None
        assert isinstance(source.connection_manager, ConnectionManagerInterface)
        
        # 测试接口调用
        success = await source.connection_manager.initialize()
        assert success is True
        
        stats = source.connection_manager.get_stats()
        assert 'reuse_rate' in stats
        
        await source.connection_manager.cleanup()
        
    @pytest.mark.asyncio
    async def test_tongdaxin_has_connection_manager(self):
        """测试 TongDaXin 数据源拥有 connection_manager"""
        source = DataSourceFactory.create_source('tongdaxin')
        
        assert source.connection_manager is not None
        assert isinstance(source.connection_manager, ConnectionManagerInterface)
        
        # 测试接口调用
        # 注意：TongDaXin 连接可能失败，我们主要验证接口存在性
        try:
            await source.connection_manager.initialize()
        except:
            pass
            
        stats = source.connection_manager.get_stats()
        assert 'pool_size' in stats or 'active_connections' in stats
        
        await source.connection_manager.cleanup()
        
    @pytest.mark.asyncio
    async def test_polymorphism(self):
        """测试多态性：统一处理不同数据源"""
        sources = [
            DataSourceFactory.create_source('mootdx'),
            DataSourceFactory.create_source('tongdaxin')
        ]
        
        for source in sources:
            manager = source.connection_manager
            assert manager is not None
            
            # 统一调用 initialize
            try:
                await manager.initialize()
            except:
                pass
                
            # 统一调用 get_stats
            stats = manager.get_stats()
            assert isinstance(stats, dict)
            
            # 统一调用 cleanup
            await manager.cleanup()

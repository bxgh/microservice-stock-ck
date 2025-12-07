import pytest
import asyncio
from unittest.mock import MagicMock
from src.models.monitor_models import ConnectionStats
from src.core.monitoring.connection_monitor import ConnectionMonitor, connection_monitor
from src.data_sources.factory import DataSourceFactory

class TestConnectionMonitor:
    """测试连接监控器"""
    
    def test_stats_model_serialization(self):
        """测试统计模型序列化"""
        stats = ConnectionStats(
            source_name="test_source",
            is_connected=True,
            pool_size=5,
            active_connections=2,
            idle_connections=3,
            total_creates=10,
            total_reuses=50,
            reuse_rate=83.3
        )
        
        data = stats.to_dict()
        assert data['source_name'] == "test_source"
        assert data['status'] == "UP"
        assert data['pool']['total'] == 5
        assert data['metrics']['reuse_rate'] == "83.3%"
        
    @pytest.mark.asyncio
    async def test_monitor_collection(self):
        """测试监控器收集逻辑"""
        monitor = ConnectionMonitor()
        
        # 模拟管理器
        mock_manager = MagicMock()
        mock_manager.get_stats.return_value = {
            'total_creates': 1,
            'total_reuses': 9,
            'reuse_rate': '90.0%',
            'pool_size': 5,
            'active_connections': 1,
            'idle_connections': 4
        }
        mock_manager.is_healthy.return_value = True
        
        monitor.register("mock_source", mock_manager)
        
        all_stats = await monitor.get_all_stats()
        
        assert "mock_source" in all_stats
        source_stats = all_stats["mock_source"]
        assert source_stats['status'] == "UP"
        assert source_stats['metrics']['reuse_rate'] == "90.0%"
        
    @pytest.mark.asyncio
    async def test_factory_integration(self):
        """测试工厂集成"""
        # 创建数据源
        source = DataSourceFactory.create_source('mootdx')
        
        # 验证是否自动注册到全局监控器
        # 注意：由于 connection_monitor 是单例，我们需要检查私有属性
        assert 'mootdx' in connection_monitor._managers
        
        # 获取统计信息
        stats = await connection_monitor.get_all_stats()
        assert 'mootdx' in stats
        assert stats['mootdx']['source_name'] == 'mootdx'
        
        # 清理
        await source.connection_manager.cleanup()
        connection_monitor.unregister('mootdx')

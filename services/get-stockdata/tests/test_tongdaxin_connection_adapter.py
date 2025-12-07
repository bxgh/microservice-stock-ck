import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.data_sources.tongdaxin.adapter import TongDaXinConnectionAdapter
from src.services.tongdaxin_client import TongDaXinClient
from src.core.interfaces import ConnectionManagerInterface

class TestTongDaXinConnectionAdapter:
    """测试 TongDaXinConnectionAdapter"""
    
    def test_implements_interface(self):
        """验证继承关系"""
        assert issubclass(TongDaXinConnectionAdapter, ConnectionManagerInterface)
        
    @pytest.mark.asyncio
    async def test_initialize_delegates_to_client(self):
        """测试 initialize 委托"""
        mock_client = MagicMock(spec=TongDaXinClient)
        mock_client.initialize = AsyncMock(return_value=True)
        
        adapter = TongDaXinConnectionAdapter(mock_client)
        result = await adapter.initialize()
        
        assert result is True
        mock_client.initialize.assert_awaited_once()
        
    @pytest.mark.asyncio
    async def test_get_connection_delegates(self):
        """测试 get_connection 委托"""
        mock_client = MagicMock(spec=TongDaXinClient)
        mock_conn = {'api': 'mock'}
        mock_client._get_connection = AsyncMock(return_value=mock_conn)
        
        adapter = TongDaXinConnectionAdapter(mock_client)
        result = await adapter.get_connection()
        
        assert result is mock_conn
        mock_client._get_connection.assert_awaited_once()
        
    @pytest.mark.asyncio
    async def test_release_connection_delegates(self):
        """测试 release_connection 委托"""
        mock_client = MagicMock(spec=TongDaXinClient)
        mock_client._release_connection = AsyncMock()
        mock_conn = {'api': 'mock'}
        
        adapter = TongDaXinConnectionAdapter(mock_client)
        await adapter.release_connection(mock_conn)
        
        mock_client._release_connection.assert_awaited_once_with(mock_conn)
        
    @pytest.mark.asyncio
    async def test_cleanup_delegates(self):
        """测试 cleanup 委托"""
        mock_client = MagicMock(spec=TongDaXinClient)
        mock_client.close = AsyncMock()
        
        adapter = TongDaXinConnectionAdapter(mock_client)
        await adapter.cleanup()
        
        mock_client.close.assert_awaited_once()
        
    def test_is_healthy_checks_client_state(self):
        """测试 is_healthy"""
        mock_client = MagicMock(spec=TongDaXinClient)
        mock_client._is_connected = True
        
        adapter = TongDaXinConnectionAdapter(mock_client)
        assert adapter.is_healthy() is True
        
        mock_client._is_connected = False
        assert adapter.is_healthy() is False
        
    def test_get_stats(self):
        """测试 get_stats"""
        mock_client = MagicMock(spec=TongDaXinClient)
        mock_client._is_connected = True
        mock_client.max_connections = 5
        mock_client._connection_pool = [
            {'in_use': True},
            {'in_use': False}
        ]
        
        adapter = TongDaXinConnectionAdapter(mock_client)
        stats = adapter.get_stats()
        
        assert stats['is_connected'] is True
        assert stats['pool_size'] == 2
        assert stats['max_connections'] == 5
        assert stats['active_connections'] == 1

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.data_sources.mootdx.connection import MootdxConnection
from src.core.interfaces import ConnectionManagerInterface

class TestMootdxConnectionManager:
    """测试 MootdxConnection 是否正确实现了 ConnectionManagerInterface"""
    
    def test_implements_interface(self):
        """验证继承关系"""
        assert issubclass(MootdxConnection, ConnectionManagerInterface)
        
    @pytest.mark.asyncio
    async def test_initialize_calls_get_client(self):
        """测试 initialize 方法"""
        with patch('src.data_sources.mootdx.connection.Quotes') as MockQuotes:
            # 模拟 Quotes.factory
            mock_client = MagicMock()
            MockQuotes.factory.return_value = mock_client
            
            conn = MootdxConnection(best_ip=False)
            
            # 调用 initialize
            success = await conn.initialize()
            
            assert success is True
            assert conn.is_connected is True
            assert conn.client is not None
            
    @pytest.mark.asyncio
    async def test_get_connection_returns_client(self):
        """测试 get_connection 方法"""
        with patch('src.data_sources.mootdx.connection.Quotes') as MockQuotes:
            mock_client = MagicMock()
            MockQuotes.factory.return_value = mock_client
            
            conn = MootdxConnection(best_ip=False)
            await conn.initialize()
            
            # 调用 get_connection
            client = await conn.get_connection()
            
            assert client is mock_client
            
    @pytest.mark.asyncio
    async def test_cleanup_calls_close(self):
        """测试 cleanup 方法"""
        conn = MootdxConnection(best_ip=False)
        conn._connected = True
        conn.client = MagicMock()
        
        # 调用 cleanup
        await conn.cleanup()
        
        assert conn.is_connected is False
        assert conn.client is None
        
    def test_is_healthy(self):
        """测试 is_healthy 方法"""
        conn = MootdxConnection(best_ip=False)
        
        # 初始状态
        assert conn.is_healthy() is False
        
        # 连接状态
        conn._connected = True
        conn.client = MagicMock()
        assert conn.is_healthy() is True
        
    def test_get_stats_interface(self):
        """测试 get_stats 方法"""
        conn = MootdxConnection(best_ip=False)
        stats = conn.get_stats()
        
        assert isinstance(stats, dict)
        assert 'total_creates' in stats
        assert 'reuse_rate' in stats

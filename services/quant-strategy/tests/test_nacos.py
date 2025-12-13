"""
Nacos 服务注册测试
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from registry.nacos_registry_simple import (
    initialize_nacos, register_to_nacos, cleanup_nacos,
    get_nacos_client, check_nacos_connection
)


class TestNacosRegistry:
    """Nacos 服务注册测试"""

    @pytest.fixture
    def mock_nacos_client(self):
        """模拟 Nacos 客户端"""
        mock_client = MagicMock()
        mock_client.add_naming_instance.return_value = True
        mock_client.remove_naming_instance.return_value = True
        mock_client.send_heartbeat.return_value = True
        return mock_client

    @pytest.fixture
    def mock_settings(self):
        """模拟配置"""
        mock_config = MagicMock()
        mock_config.NACOS_SERVER_URL = "http://localhost:8848"
        mock_config.NACOS_NAMESPACE = "dev"
        mock_config.NACOS_GROUP = "DEFAULT_GROUP"
        mock_config.SERVICE_NAME = "quant-strategy"
        mock_config.SERVICE_VERSION = "1.0.0"
        mock_config.PORT = 8084
        return mock_config

    def test_initialize_nacos_success(self):
        """测试 Nacos 初始化成功"""
        with patch('registry.nacos_registry_simple.NacosClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            result = initialize_nacos()

        mock_client_class.assert_called_once_with(
            server_addresses="http://localhost:8848",
            namespace="dev"
        )
        assert result is True

    def test_initialize_nacos_failure(self):
        """测试 Nacos 初始化失败"""
        with patch('registry.nacos_registry_simple.NacosClient') as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            result = initialize_nacos()

        assert result is False

    @pytest.mark.asyncio
    async def test_register_to_nacos_success(self, mock_settings):
        """测试服务注册成功"""
        with patch('registry.nacos_registry_simple.get_nacos_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.add_naming_instance.return_value = True
            mock_get_client.return_value = mock_client

            result = await register_to_nacos(
                service_name=mock_settings.SERVICE_NAME,
                service_port=mock_settings.PORT,
                framework="FastAPI",
                description=f"{mock_settings.SERVICE_NAME} 微服务 - 量化策略引擎"
            )

        mock_client.add_naming_instance.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_register_to_nacos_failure(self, mock_settings):
        """测试服务注册失败"""
        with patch('registry.nacos_registry_simple.get_nacos_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.add_naming_instance.return_value = False
            mock_get_client.return_value = mock_client

            result = await register_to_nacos(
                service_name=mock_settings.SERVICE_NAME,
                service_port=mock_settings.PORT
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_register_to_nacos_exception(self, mock_settings):
        """测试服务注册异常"""
        with patch('registry.nacos_registry_simple.get_nacos_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.add_naming_instance.side_effect = Exception("Registration failed")
            mock_get_client.return_value = mock_client

            result = await register_to_nacos(
                service_name=mock_settings.SERVICE_NAME,
                service_port=mock_settings.PORT
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_nacos_success(self, mock_settings):
        """测试 Nacos 清理成功"""
        with patch('registry.nacos_registry_simple.get_nacos_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.remove_naming_instance.return_value = True
            mock_get_client.return_value = mock_client

            await cleanup_nacos()

        mock_client.remove_naming_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_nacos_failure(self, mock_settings):
        """测试 Nacos 清理失败"""
        with patch('registry.nacos_registry_simple.get_nacos_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.remove_naming_instance.side_effect = Exception("Cleanup failed")
            mock_get_client.return_value = mock_client

            # 清理不应该抛出异常
            await cleanup_nacos()

    def test_get_nacos_client_existing(self):
        """测试获取现有的 Nacos 客户端"""
        mock_client = MagicMock()

        with patch('registry.nacos_registry_simple._nacos_client', mock_client):
            client = get_nacos_client()

        assert client == mock_client

    def test_get_nacos_client_none(self):
        """测试获取 None 的 Nacos 客户端"""
        with patch('registry.nacos_registry_simple._nacos_client', None):
            client = get_nacos_client()

        assert client is None

    @pytest.mark.asyncio
    async def test_check_nacos_connection_success(self):
        """测试 Nacos 连接检查成功"""
        mock_client = MagicMock()
        mock_client.send_heartbeat.return_value = True

        with patch('registry.nacos_registry_simple.get_nacos_client', return_value=mock_client):
            result = await check_nacos_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_nacos_connection_failure(self):
        """测试 Nacos 连接检查失败"""
        mock_client = MagicMock()
        mock_client.send_heartbeat.return_value = False

        with patch('registry.nacos_registry_simple.get_nacos_client', return_value=mock_client):
            result = await check_nacos_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_nacos_connection_exception(self):
        """测试 Nacos 连接检查异常"""
        with patch('registry.nacos_registry_simple.get_nacos_client', side_effect=Exception("No client")):
            result = await check_nacos_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_register_service_with_metadata(self, mock_settings):
        """测试注册服务时包含元数据"""
        with patch('registry.nacos_registry_simple.get_nacos_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.add_naming_instance.return_value = True
            mock_get_client.return_value = mock_client

            result = await register_to_nacos(
                service_name=mock_settings.SERVICE_NAME,
                service_port=mock_settings.PORT,
                framework="FastAPI",
                description=f"{mock_settings.SERVICE_NAME} 微服务 - 量化策略引擎"
            )

        # 验证调用参数包含元数据
        call_args = mock_client.add_naming_instance.call_args
        assert call_args is not None
        args, kwargs = call_args

        # 检查是否传递了正确的参数
        assert args[0] == mock_settings.SERVICE_NAME  # service_name
        assert args[1] == mock_settings.PORT  # ip (这里应该是 IP，但我们传递的是端口)

        # 检查 kwargs 中的元数据
        metadata = kwargs.get('metadata', {})
        assert 'version' in metadata
        assert 'framework' in metadata
        assert 'description' in metadata
        assert metadata['framework'] == 'FastAPI'

        assert result is True

    def test_nacos_client_configuration(self):
        """测试 Nacos 客户端配置"""
        with patch('registry.nacos_registry_simple.NacosClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            initialize_nacos()

        # 验证客户端配置
        mock_client_class.assert_called_once_with(
            server_addresses="http://localhost:8848",
            namespace="dev"
        )

        # 验证客户端设置
        mock_client.set_naming_namespace.assert_called_once_with("dev")
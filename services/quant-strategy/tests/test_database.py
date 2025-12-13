"""
数据库模块测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio

from core.database import (
    get_mysql_session, get_async_mysql_session, get_redis,
    get_clickhouse_client, check_mysql_health, check_redis_health,
    check_clickhouse_health, check_all_databases, init_databases,
    close_databases
)


class TestDatabaseConnections:
    """数据库连接测试"""

    @pytest.fixture
    def mock_mysql_engine(self):
        """模拟 MySQL 引擎"""
        with patch('core.database.mysql_engine') as mock_engine:
            yield mock_engine

    @pytest.fixture
    def mock_mysql_async_engine(self):
        """模拟异步 MySQL 引擎"""
        with patch('core.database.mysql_async_engine') as mock_engine:
            yield mock_engine

    @pytest.fixture
    def mock_redis_pool(self):
        """模拟 Redis 连接池"""
        with patch('core.database.redis_pool', None) as mock_pool:
            yield mock_pool

    @pytest.fixture
    def mock_clickhouse_client(self):
        """模拟 ClickHouse 客户端"""
        with patch('core.database.clickhouse_client', None) as mock_client:
            yield mock_client

    def test_get_mysql_session(self, mock_mysql_engine):
        """测试获取 MySQL 会话"""
        mock_session = MagicMock()
        mock_session_local = MagicMock(return_value=mock_session)

        with patch('core.database.MySQLSessionLocal', mock_session_local):
            session = get_mysql_session()

        mock_session_local.assert_called_once()
        mock_session.close.assert_called_once()

        # 验证返回的是会话对象
        assert session == mock_session

    @pytest.mark.asyncio
    async def test_get_async_mysql_session(self, mock_mysql_async_engine):
        """测试获取异步 MySQL 会话"""
        mock_session = AsyncMock()
        mock_async_session_local = MagicMock(return_value=mock_session)

        with patch('core.database.AsyncMySQLSessionLocal', mock_async_session_local):
            async for session in get_async_mysql_session():
                assert session == mock_session
                break  # 只测试第一次迭代

        mock_async_session_local.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_new_connection(self):
        """测试创建新的 Redis 连接"""
        mock_redis = AsyncMock()
        mock_from_url = AsyncMock(return_value=mock_redis)

        with patch('core.database.from_url', mock_from_url):
            with patch('core.database.redis_pool', None):
                redis_client = await get_redis()

        mock_from_url.assert_called_once_with(
            "redis://localhost:6379/0",
            password=None,
            max_connections=50,
            retry_on_timeout=True,
            decode_responses=True
        )

        assert redis_client == mock_redis

    @pytest.mark.asyncio
    async def test_get_redis_existing_connection(self):
        """测试获取现有的 Redis 连接"""
        mock_redis = AsyncMock()

        with patch('core.database.redis_pool', mock_redis):
            redis_client = await get_redis()

        assert redis_client == mock_redis

    def test_get_clickhouse_client_new_connection(self):
        """测试创建新的 ClickHouse 客户端"""
        mock_client = MagicMock()
        mock_client_class = MagicMock(return_value=mock_client)

        with patch('core.database.clickhouse_driver.Client', mock_client_class):
            with patch('core.database.clickhouse_client', None):
                client = get_clickhouse_client()

        mock_client_class.assert_called_once_with(
            host="localhost",
            port=8123,
            database="stock_data_dev",
            user="default",
            password="",
            compression=True
        )

        assert client == mock_client

    def test_get_clickhouse_client_existing_connection(self):
        """测试获取现有的 ClickHouse 客户端"""
        mock_client = MagicMock()

        with patch('core.database.clickhouse_client', mock_client):
            client = get_clickhouse_client()

        assert client == mock_client

    @pytest.mark.asyncio
    async def test_check_mysql_health_success(self):
        """测试 MySQL 健康检查成功"""
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 1

        with patch('core.database.mysql_async_engine') as mock_engine:
            mock_engine.connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.execute.return_value = mock_result

            result = await check_mysql_health()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_mysql_health_failure(self):
        """测试 MySQL 健康检查失败"""
        with patch('core.database.mysql_async_engine') as mock_engine:
            mock_engine.connect.side_effect = Exception("Connection failed")

            result = await check_mysql_health()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_redis_health_success(self):
        """测试 Redis 健康检查成功"""
        mock_redis = AsyncMock()

        with patch('core.database.get_redis', return_value=mock_redis):
            result = await check_redis_health()

        mock_redis.ping.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_redis_health_failure(self):
        """测试 Redis 健康检查失败"""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Redis error")

        with patch('core.database.get_redis', return_value=mock_redis):
            result = await check_redis_health()

        assert result is False

    def test_check_clickhouse_health_success(self):
        """测试 ClickHouse 健康检查成功"""
        mock_client = MagicMock()
        mock_client.execute.return_value = [(1,)]

        with patch('core.database.get_clickhouse_client', return_value=mock_client):
            result = check_clickhouse_health()

        mock_client.execute.assert_called_once_with("SELECT 1")
        assert result is True

    def test_check_clickhouse_health_failure(self):
        """测试 ClickHouse 健康检查失败"""
        mock_client = MagicMock()
        mock_client.execute.side_effect = Exception("ClickHouse error")

        with patch('core.database.get_clickhouse_client', return_value=mock_client):
            result = check_clickhouse_health()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_all_databases(self):
        """测试检查所有数据库"""
        with patch('core.database.check_mysql_health', return_value=True) as mock_mysql, \
             patch('core.database.check_redis_health', return_value=True) as mock_redis, \
             patch('core.database.check_clickhouse_health', return_value=False) as mock_clickhouse:

            result = await check_all_databases()

        mock_mysql.assert_called_once()
        mock_redis.assert_called_once()
        mock_clickhouse.assert_called_once()

        expected = {
            "mysql": True,
            "redis": True,
            "clickhouse": False,
            "overall": False  # 因为 ClickHouse 失败
        }

        assert result == expected

    @pytest.mark.asyncio
    async def test_init_databases_success(self):
        """测试数据库初始化成功"""
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 1
        mock_redis = AsyncMock()
        mock_client = MagicMock()
        mock_client.execute.return_value = [(1,)]

        with patch('core.database.mysql_async_engine') as mock_mysql_engine, \
             patch('core.database.get_redis', return_value=mock_redis), \
             patch('core.database.get_clickhouse_client', return_value=mock_client):

            mock_mysql_engine.connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.execute.return_value = mock_result

            await init_databases()

        # 验证所有数据库都被测试
        mock_mysql_engine.connect.assert_called_once()
        mock_redis.ping.assert_called_once()
        mock_client.execute.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_init_databases_failure(self):
        """测试数据库初始化失败"""
        with patch('core.database.mysql_async_engine') as mock_engine:
            mock_engine.connect.side_effect = Exception("MySQL connection failed")

            with pytest.raises(Exception, match="MySQL connection failed"):
                await init_databases()

    @pytest.mark.asyncio
    async def test_close_databases(self):
        """测试关闭数据库连接"""
        mock_redis = AsyncMock()
        mock_mysql_async_engine = AsyncMock()
        mock_mysql_engine = MagicMock()
        mock_client = MagicMock()

        with patch('core.database.redis_pool', mock_redis), \
             patch('core.database.mysql_async_engine', mock_mysql_async_engine), \
             patch('core.database.mysql_engine', mock_mysql_engine), \
             patch('core.database.clickhouse_client', mock_client):

            await close_databases()

        mock_redis.close.assert_called_once()
        mock_mysql_async_engine.dispose.assert_called_once()
        mock_mysql_engine.dispose.assert_called_once()
        mock_client.disconnect.assert_called_once()
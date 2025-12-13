"""
配置模块测试
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from config.settings import settings


class TestSettings:
    """配置设置测试"""

    def test_default_values(self):
        """测试默认配置值"""
        assert settings.SERVICE_NAME == "quant-strategy"
        assert settings.SERVICE_VERSION == "1.0.0"
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8084
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT == "json"

    def test_mysql_config(self):
        """测试 MySQL 配置"""
        assert settings.MYSQL_HOST == "localhost"
        assert settings.MYSQL_PORT == 3306
        assert settings.MYSQL_DATABASE == "microservice_stock_dev"
        assert settings.MYSQL_USERNAME == "root"
        assert settings.MYSQL_PASSWORD == "root123456"
        assert settings.MYSQL_POOL_SIZE == 20
        assert settings.MYSQL_MAX_OVERFLOW == 30

    def test_redis_config(self):
        """测试 Redis 配置"""
        assert settings.REDIS_HOST == "localhost"
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_DATABASE == 0
        assert settings.REDIS_PASSWORD is None
        assert settings.REDIS_POOL_SIZE == 50

    def test_clickhouse_config(self):
        """测试 ClickHouse 配置"""
        assert settings.CLICKHOUSE_HOST == "localhost"
        assert settings.CLICKHOUSE_PORT == 8123
        assert settings.CLICKHOUSE_DATABASE == "stock_data_dev"
        assert settings.CLICKHOUSE_USERNAME is None
        assert settings.CLICKHOUSE_PASSWORD is None

    def test_nacos_config(self):
        """测试 Nacos 配置"""
        assert settings.NACOS_SERVER_URL == "http://localhost:8848"
        assert settings.NACOS_NAMESPACE == "dev"
        assert settings.NACOS_GROUP == "DEFAULT_GROUP"

    @patch.dict(os.environ, {
        'SERVICE_NAME': 'test-service',
        'SERVICE_VERSION': '2.0.0',
        'HOST': '127.0.0.1',
        'PORT': '9999',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_environment_variable_override(self):
        """测试环境变量覆盖配置"""
        # 重新加载设置以反映环境变量
        from config.settings import Settings
        test_settings = Settings()

        assert test_settings.SERVICE_NAME == 'test-service'
        assert test_settings.SERVICE_VERSION == '2.0.0'
        assert test_settings.HOST == '127.0.0.1'
        assert test_settings.PORT == 9999
        assert test_settings.LOG_LEVEL == 'DEBUG'

    def test_case_sensitivity(self):
        """测试配置的大小写敏感性"""
        # 确保配置使用大写命名
        config_fields = [
            'SERVICE_NAME', 'SERVICE_VERSION', 'HOST', 'PORT',
            'MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_DATABASE',
            'REDIS_HOST', 'REDIS_PORT', 'CLICKHOUSE_HOST',
            'NACOS_SERVER_URL', 'LOG_LEVEL', 'LOG_FORMAT'
        ]

        for field in config_fields:
            assert hasattr(settings, field)
            # 确保没有对应的小写版本
            assert not hasattr(settings, field.lower())

    def test_optional_fields(self):
        """测试可选字段"""
        # 这些字段应该允许为 None
        assert settings.REDIS_PASSWORD is None
        assert settings.CLICKHOUSE_USERNAME is None
        assert settings.CLICKHOUSE_PASSWORD is None
        assert settings.API_KEY is None
        assert settings.JWT_SECRET is None

    def test_numeric_values(self):
        """测试数值类型配置"""
        assert isinstance(settings.PORT, int)
        assert isinstance(settings.MYSQL_PORT, int)
        assert isinstance(settings.CLICKHOUSE_PORT, int)
        assert isinstance(settings.REDIS_PORT, int)
        assert isinstance(settings.REDIS_DATABASE, int)
        assert isinstance(settings.MYSQL_POOL_SIZE, int)
        assert isinstance(settings.MYSQL_MAX_OVERFLOW, int)
        assert isinstance(settings.REDIS_POOL_SIZE, int)

    def test_boolean_values(self):
        """测试布尔类型配置"""
        assert isinstance(settings.MONITORING_ENABLED, bool)
        assert isinstance(settings.BACKTEST_ENABLED, bool)
        assert isinstance(settings.ACCESS_LOG, bool)
        assert isinstance(settings.DEBUG, bool)

    def test_string_values(self):
        """测试字符串类型配置"""
        string_fields = [
            'SERVICE_NAME', 'SERVICE_VERSION', 'HOST',
            'NACOS_SERVER_URL', 'NACOS_NAMESPACE', 'NACOS_GROUP',
            'MYSQL_HOST', 'MYSQL_DATABASE', 'MYSQL_USERNAME', 'MYSQL_PASSWORD',
            'REDIS_HOST', 'CLICKHOUSE_HOST', 'CLICKHOUSE_DATABASE',
            'LOG_LEVEL', 'LOG_FORMAT', 'TIMEZONE'
        ]

        for field in string_fields:
            value = getattr(settings, field)
            assert isinstance(value, str)
            assert len(value) > 0
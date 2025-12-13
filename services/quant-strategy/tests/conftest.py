"""
pytest 配置文件
"""

import sys
import os
import pytest

# 将 src 目录添加到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 设置测试环境变量
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['LOG_FORMAT'] = 'json'  # 保持 json 格式以便测试
os.environ['SERVICE_NAME'] = 'test-quant-strategy'
os.environ['SERVICE_VERSION'] = '1.0.0-test'

@pytest.fixture(scope="session")
def test_config():
    """测试配置 fixture"""
    return {
        'test_mode': True,
        'mock_databases': True,
        'mock_nacos': True,
        'log_level': 'DEBUG'
    }

@pytest.fixture(autouse=True)
def setup_test_environment(test_config):
    """自动应用的测试环境设置"""
    # 设置测试环境变量
    os.environ['TESTING'] = 'true'
    yield
    # 清理测试环境
    if 'TESTING' in os.environ:
        del os.environ['TESTING']
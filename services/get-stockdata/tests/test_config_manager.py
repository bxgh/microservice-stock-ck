"""
Test StockPoolConfigManager

Story 004.05: Stock Pool Configuration Management
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from services.stock_pool.config_manager import StockPoolConfigManager


@pytest.fixture
def sample_config():
    """示例配置"""
    return {
        'version': '2.0.0',
        'updated_at': '2025-12-02T10:00:00+08:00',
        'active_mode': 'hs300_top100',
        'global': {
            'default_acquisition_interval': 3,
            'max_pool_size': 1000
        },
        'hs300_top100': {
            'enabled': True,
            'size': 100
        },
        'blacklist': {
            'enabled': True,
            'patterns': ['ST*', '*ST*', '退*'],
            'codes': [],
            'rules': []
        },
        'whitelist': {
            'enabled': False,
            'codes': []
        }
    }


@pytest.mark.asyncio
async def test_load_config_success(tmp_path, sample_config):
    """测试成功加载配置"""
    # 创建临时配置文件
    config_file = tmp_path / "test_config.yaml"
    
    with patch('builtins.open', mock_open(read_data="version: '2.0.0'\nactive_mode: 'hs300_top100'\nglobal:\n  default_acquisition_interval: 3")):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('yaml.safe_load', return_value=sample_config):
                manager = StockPoolConfigManager(config_path=str(config_file))
                config = await manager.load_config()
                
                assert config['version'] == '2.0.0'
                assert manager.config_version == '2.0.0'


@pytest.mark.asyncio
async def test_validate_config_success(sample_config):
    """测试配置验证通过"""
    manager = StockPoolConfigManager()
    
    # 不应抛出异常
    manager._validate_config(sample_config)


@pytest.mark.asyncio
async def test_validate_config_missing_version():
    """测试配置缺少version字段"""
    manager = StockPoolConfigManager()
    invalid_config = {'active_mode': 'hs300_top100'}
    
    with pytest.raises(ValueError, match="配置文件缺少必需字段"):
        manager._validate_config(invalid_config)


@pytest.mark.asyncio
async def test_validate_config_invalid_mode():
    """测试无效的active_mode"""
    manager = StockPoolConfigManager()
    invalid_config = {
        'version': '2.0.0',
        'active_mode': 'invalid_mode',
        'global': {}
    }
    
    with pytest.raises(ValueError, match="无效的 active_mode"):
        manager._validate_config(invalid_config)


@pytest.mark.asyncio
async def test_blacklist_check_pattern(sample_config):
    """测试黑名单模式匹配"""
    with patch('builtins.open', mock_open()):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('yaml.safe_load', return_value=sample_config):
                manager = StockPoolConfigManager()
                await manager.load_config()
                
                # ST股应被拉黑
                assert manager.is_blacklisted('600000', {'名称': 'ST平安'}) == True
                
                # 正常股不应被拉黑
                assert manager.is_blacklisted('600519', {'名称': '贵州茅台'}) == False


@pytest.mark.asyncio
async def test_blacklist_check_code(sample_config):
    """测试黑名单代码匹配"""
    sample_config['blacklist']['codes'] = ['600000']
    
    with patch('builtins.open', mock_open()):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('yaml.safe_load', return_value=sample_config):
                manager = StockPoolConfigManager()
                await manager.load_config()
                
                # 在黑名单代码中
                assert manager.is_blacklisted('600000', None) == True
                
                # 不在黑名单中
                assert manager.is_blacklisted('600519', None) == False


@pytest.mark.asyncio
async def test_whitelist_priority(sample_config):
    """测试白名单优先级高于黑名单"""
    sample_config['whitelist']['enabled'] = True
    sample_config['whitelist']['codes'] = ['600000']
    sample_config['blacklist']['codes'] = ['600000']
    
    with patch('builtins.open', mock_open()):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('yaml.safe_load', return_value=sample_config):
                manager = StockPoolConfigManager()
                await manager.load_config()
                
                # 在白名单中，不应被拉黑
                assert manager.is_blacklisted('600000', None) == False


@pytest.mark.asyncio
async def test_get_active_pool_config(sample_config):
    """测试获取激活的股票池配置"""
    with patch('builtins.open', mock_open()):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('yaml.safe_load', return_value=sample_config):
                manager = StockPoolConfigManager()
                await manager.load_config()
                
                active_config = manager.get_active_pool_config()
                assert active_config['enabled'] == True
                assert active_config['size'] == 100


@pytest.mark.asyncio
async def test_register_reload_callback():
    """测试注册重载回调"""
    manager = StockPoolConfigManager()
    
    callback_called = False
    
    async def test_callback(config):
        nonlocal callback_called
        callback_called = True
    
    manager.register_reload_callback(test_callback)
    
    assert len(manager.reload_callbacks) == 1


@pytest.mark.asyncio
async def test_config_summary():
    """测试配置摘要"""
    manager = StockPoolConfigManager()
    manager.config_version = '2.0.0'
    manager.config = {'active_mode': 'hs300_top100'}
    
    summary = manager.get_config_summary()
    
    assert summary['version'] == '2.0.0'
    assert summary['active_mode'] == 'hs300_top100'
    assert 'watching' in summary
